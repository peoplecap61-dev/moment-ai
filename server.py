
import os, json, shutil, subprocess, uuid
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from openai import OpenAI

BASE = Path(__file__).parent
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"
UPLOADS.mkdir(exist_ok=True); OUTPUTS.mkdir(exist_ok=True)
app = FastAPI(title="Moment AI Clip Generator")
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS)), name="outputs")

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-1800:])
    return p.stdout

@app.get("/")
def home():
    return FileResponse(BASE / "static" / "index.html")

@app.get("/api/health")
def health():
    return {"status":"ok", "ai_configured":bool(os.getenv("OPENAI_API_KEY")), "ffmpeg":shutil.which("ffmpeg") is not None}

@app.post("/api/jobs")
async def create_job(video: UploadFile = File(...), quality: str = Form("720p"), count: int = Form(5)):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(503, "Server owner must configure OPENAI_API_KEY.")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise HTTPException(503, "Server needs FFmpeg and FFprobe installed.")
    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(400, "Please upload a video file.")
    allowed = {"360p":360, "400p":400, "480p":480, "720p":720, "1080p":1080}
    if quality not in allowed: raise HTTPException(400, "Unsupported quality.")
    count = max(1, min(count, 10))
    job = uuid.uuid4().hex[:12]
    source = UPLOADS / f"{job}_{Path(video.filename or 'video').name}"
    with source.open("wb") as out:
        shutil.copyfileobj(video.file, out)
    audio = UPLOADS / f"{job}.mp3"
    try:
        run(["ffmpeg","-y","-i",str(source),"-vn","-ac","1","-ar","16000","-b:a","64k",str(audio)])
        client = OpenAI()
        with audio.open("rb") as f:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=f, response_format="verbose_json", timestamp_granularities=["segment"])
        segments = getattr(transcript, "segments", None) or []
        if not segments:
            raise HTTPException(422, "Could not obtain timestamped transcript for this video.")
        compact = [{"start":round(s.start,2),"end":round(s.end,2),"text":s.text} for s in segments]
        prompt = (
          "Select up to "+str(count)+" compelling short-video moments from this transcript. "
          "Each must be 20-60 seconds, fit within the transcript, and have a clear hook/payoff. "
          "Choose category only from reaction, epic, ideas, funny. Avoid overlapping clips. "
          "Return ONLY JSON: {\"clips\":[{\"start\":number,\"end\":number,\"category\":\"funny\",\"reason\":\"short reason\"}]}. "
          "Do not claim virality. Transcript: "+json.dumps(compact,ensure_ascii=False)
        )
        response = client.chat.completions.create(
          model=os.getenv("MOMENT_AI_TEXT_MODEL","gpt-4o-mini"),
          messages=[{"role":"user","content":prompt}],
          response_format={"type":"json_object"}
        )
        chosen = json.loads(response.choices[0].message.content or "{}").get("clips",[])
        meta = run(["ffprobe","-v","error","-show_entries","format=duration","-of","json",str(source)])
        duration = float(json.loads(meta)["format"]["duration"])
        clips=[]
        for i,c in enumerate(chosen[:count]):
            start=max(0,float(c.get("start",0))); end=min(duration,float(c.get("end",start+30)))
            if end-start < 8: continue
            out=OUTPUTS/f"{job}_{i+1}.mp4"
            h=allowed[quality]
            # Vertical 9:16 canvas, scale/crop source, H.264 MP4.
            vf=f"scale=ih*9/16:ih:force_original_aspect_ratio=increase,crop=ih*9/16:ih,scale=-2:{h}"
            run(["ffmpeg","-y","-ss",str(start),"-i",str(source),"-t",str(end-start),"-vf",vf,
                 "-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-movflags","+faststart",str(out)])
            clips.append({"category":str(c.get("category","moment")),"start":round(start,1),"end":round(end,1),"url":f"/outputs/{out.name}","reason":str(c.get("reason",""))})
        return {"status":"completed","message":f"{len(clips)} clips rendered. Review them before publishing.","clips":clips}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, "Processing failed: "+str(e)[:500])
    finally:
        # Keep source/audio for debugging only if explicitly configured.
        if os.getenv("KEEP_UPLOADS") != "1":
            source.unlink(missing_ok=True); audio.unlink(missing_ok=True)
