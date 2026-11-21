MOMENT AI — AI CLIP STARTER

यह पहले से मौजूद UI से आगे का वास्तविक backend starter है:
1. यूजर अपने/अनुमति वाले वीडियो की फाइल अपलोड करता है।
2. FFmpeg audio निकालता है।
3. OpenAI transcription API timestamp वाले segments देता है।
4. AI transcript से reaction/epic/ideas/funny moments चुनता है।
5. FFmpeg चुने हुए समय से vertical MP4 clips बनाता है।
6. UI में डाउनलोड लिंक दिखते हैं।

जरूरी सीमाएँ:
- यह YouTube URL डाउनलोड नहीं करता। YouTube लिंक से वीडियो निकालना बिना अधिकार/अनुमति के नहीं किया गया है।
- अभी वीडियो FILE UPLOAD workflow है।
- इसे ऑनलाइन चलाने के लिए Python server, FFmpeg/FFprobe, OpenAI API key और API billing/credits चाहिए।
- API key केवल server environment में रखें; HTML/फोन में कभी न डालें।
- AI चुने हुए moments गलत भी चुन सकता है; प्रकाशित करने से पहले हर clip review करें।
- Vertical crop center-crop है; subject framing की manual review करें।
- यह demo production-grade queue, user accounts, rate limits, payment gateway, privacy/deletion controls और storage lifecycle के बिना है।

SERVER SETUP (कंप्यूटर/क्लाउड server पर):
1. Python 3.10+ और FFmpeg/FFprobe install करें।
2. pip install -r requirements.txt
3. OPENAI_API_KEY को server environment में set करें।
4. uvicorn server:app --host 0.0.0.0 --port 8000
5. Browser में server URL खोलें।

Android-only note:
Android फोन से code ZIP download कर सकते हैं, लेकिन production video processing फोन के browser में नहीं चलेगी। इसे cloud server पर deploy करना होगा। Hosting account owner/user को खुद बनाना और authorize करना होगा।
