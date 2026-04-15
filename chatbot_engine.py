from google import genai
from google.genai import types
import os
import re
import uuid
import time
from database import get_db_connection
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator

# For consistent language detection results
DetectorFactory.seed = 0

# Configuration constants
MAX_RETRIES = 1
DEFAULT_RETRY_DELAY = 1.0  # seconds
MAX_TOKENS = 1000
MODEL_PRIORITY = [
    'gemini-1.5-flash-8b',    # Often has separate/higher availability
    'gemini-flash-latest',    # Shown to work in user logs (returned 429)
    'gemini-1.5-flash',
    'gemini-2.0-flash',
]

class MuseumChatbot:
    def __init__(self):
        """Initializes the chatbot engine with a verified AI model."""
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.model_id = None
        self.booking_marker = "[INIT_BOOKING]"
        self._init_templates()
        
        print(f"INFO: Initializing MuseumChatbot Engine...")
        if not self.api_key:
            print("WARNING: GEMINI_API_KEY not found. Operating in Rule-Based Fallback mode.")
        else:
            self._initialize_ai()
    
    def _init_templates(self):
        """Initializes the static conversational phrases and maps."""
        # Conversational Phrases Library (as suggested by the user)
        self.templates = {
            'greeting': {
                'en': "Hello! How can I help you today?",
                'hi_native': "नमस्ते! मैं आपकी कैसे मदद कर सकता हूँ?",
                'hi_latin': "Namaste! Kaise help kar sakta hoon?",
                'ta_native': "வணக்கம்! நான் எப்படி உதவலாம்?",
                'ta_latin': "Vanakkam! Naan eppadi help pannalaam?",
                'pa_native': "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
                'pa_latin': "Sat Sri Akal! Tuhadi kiven madad karaan?",
                'bn_native': "নমস্কার! আমি কীভাবে সাহায্য করতে পারি?",
                'bn_latin': "Nomoskar! Ami kivabe help korte pari?",
                'te_native': "నమస్తే! నేను ఎలా సహాయం చేయగలను?",
                'te_latin': "Namaste! Nenu ela help cheyagalanu?",
                'kn_native': "ನಮಸ್ಕಾರ! ನಾನು ಹೇಗೆ సహాయ ಮಾಡಬಹುದು?",
                'kn_latin': "Namaskara! Naanu hege help madabahudu?",
                'ml_native': "നമസ്കാരം! ഞാൻ എങ്ങനെ സഹായിക്കാം?",
                'ml_latin': "Namaskaram! Njan engane help cheyyam?",
                'gu_native': "નમસ્તે! હું તમારી કેવી રીતે મદદ કરી શકું?",
                'gu_latin': "Namaste! Hu tamari kem madad kari saku?",
                'mr_native': "नमस्कार! मी तुम्हाला कशी मदत करू शकतो?",
                'mr_latin': "Namaskar! Mi tumhala kashi madat karu shakto?"
            },
            'booking_start': {
                'en': "I can definitely help with tickets. Reply with the number of your choice:<br>",
                'hi_native': "ज़रूर! किस प्रदर्शनी के लिए टिकट चाहिए? नंबर दें:<br>",
                'hi_latin': "Zaroor! Kaunsi gallery ke liye booking karni hai? Number batayein:<br>",
                'ta_native': "நிச்சயமாக டிக்கெட்டுகளுக்கு உதவ முடியும். உங்களுக்கு விருப்பமான எண்ணுடன் பதிலளிக்கவும்:<br>",
                'ta_latin': "Sure! Tickets book panna help pannuven. Choice number-a reply pannunga:<br>",
                'pa_native': "ਬਿਲਕੁਲ ਮੈਂ ਟਿਕਟਾਂ ਵਿੱਚ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ। ਆਪਣੀ ਪਸੰਦ ਦੇ ਨੰਬਰ ਨਾਲ ਜਵਾਬ ਦਿਓ:<br>",
                'pa_latin': "Zaroor! Main tickets ch madad kar sakda haan. Choice number dasso:<br>"
            },
            'ticket_count': {
                'en': "Great choice: {title}. How many tickets would you like to book?",
                'hi_native': "अच्छा चुनाव: {title}। आप कितने टिकट बुक करना चाहते हैं?",
                'hi_latin': "Badhiya choice: {title}! Aap kitne tickets lena chahte ho?",
                'ta_native': "சிறந்த தேர்வு: {title}. உங்களுக்கு எத்தனை டிக்கெட்டுகள் வேண்டும்?",
                'ta_latin': "Nalla choice: {title}. Ungalukku ethana tickets venum?",
                'pa_native': "ਵਧੀਆ ਚੋਣ: {title}। ਤੁਸੀਂ ਕਿੰਨੀਆਂ ਟਿਕਟਾਂ ਬੁੱਕ ਕਰਨਾ ਚਾਹੁੰਦੇ ਹੋ?",
                'pa_latin': "Wadiya choice: {title}. Tusi kinniyan ticktan book karna chaunde ho?"
            },
            'payment_confirm': {
                'en': "Confirming {count} tickets for '{title}'. Total is ₹{total}. Proceed?",
                'hi_native': "क्या मैं '{title}' के लिए {count} टिकट पक्के कर दूँ? कुल ₹{total} है।",
                'hi_latin': "Confirming {count} tickets for '{title}'. Total ₹{total} ho gaya. Chalein aage?",
                'ta_native': "உறுதிப்படுத்துகிறோம் {count} டிக்கெட்டுகள் '{title}' க்காக. மொத்தம் ₹{total}. தொடரலாமா?",
                'ta_latin': "Confirming {count} tickets for '{title}'. Total ₹{total} varudhu. Proceed pannalama?",
                'pa_native': "ਪੁਸ਼ਟੀ ਕਰ ਰਹੇ ਹਾਂ {count} ਟਿਕਟਾਂ '{title}' ਲਈ। ਕੁੱਲ ₹{total} ਹੈ। ਅੱਗੇ ਵਧੀਏ?",
                'pa_latin': "Confirming {count} tickets for '{title}'. Total ₹{total} ho gaya. Agge vadhye?"
            },
            'hours': {
                'en': "Museum Hours: 9:00 AM - 6:00 PM (Tue-Sun). Closed Mondays.",
                'hi_native': "संग्रहालय का समय: सुबह 9:00 - शाम 6:00 (मंगलवार-रविवार)। सोमवार को बंद रहता है।",
                'hi_latin': "Museum timings: 9:00 AM se 6:00 PM (Tue-Sun). Monday ko band rehta hai.",
                'ta_native': "அருங்காட்சியக நேரம்: காலை 9:00 - மாலை 6:00 (செவ்வாய்-ஞாயிறு). திங்கள் கிழமை விடுமுறை.",
                'ta_latin': "Museum timings: 9:00 AM to 6:00 PM (Tue-Sun). Monday leave.",
                'pa_native': "ਅਜਾਇਬ ਘਰ ਦਾ ਸਮਾਂ: ਸਵੇਰੇ 9:00 - ਸ਼ਾਮ 6:00 (ਮੰਗਲਵਾਰ-ਐਤਵਾਰ)। ਸੋਮਵਾਰ ਨੂੰ ਬੰਦ ਰਹਿੰਦਾ ਹੈ।",
                'pa_latin': "Museum timings: 9:00 AM se 6:00 PM (Tue-Sun). Monday band hunda hai."
            },
            'parking': {
                'en': "We have valet parking available in the North Wing. It is free for visitors.",
                'hi_native': "हमारे पास नॉर्थ विंग में वैलेट पार्किंग उपलब्ध है। यह आगंतुकों के लिए निःशुल्क है।",
                'hi_latin': "North Wing mein valet parking available hai. Visitors ke liye ye free hai.",
                'ta_native': "வடக்குப் பகுதியில் வாகன நிறுத்துமிடம் உள்ளது. பார்வையாளர்களுக்கு இது இலவசம்.",
                'ta_latin': "North Wing-la parking facility iruku. Idhu free service.",
                'pa_native': "ਸਾਡੇ ਕੋਲ ਉੱਤਰੀ ਵਿੰਗ ਵਿੱਚ ਪਾਰਕਿੰਗ ਉਪਲਬਧ ਹੈ। ਸੈਲਾਨੀਆਂ ਲਈ ਇਹ ਮੁਫਤ ਹੈ।",
                'pa_latin': "North Wing ch parking available hai. Visitors layi eh free hai."
            },
            'cafe': {
                'en': "The Curator's Cafe is on the 2nd floor, open until 5 PM.",
                'hi_native': "क्यूरेटर का कैफे दूसरी मंजिल पर है, शाम 5 बजे तक खुला रहता है।",
                'hi_latin': "Curator's Cafe 2nd floor par hai, shaam 5 baje tak khula rehta hai.",
                'ta_native': "கியூரேட்டர் உணவகம் 2வது மாடியில் உள்ளது, மாலை 5 மணி வரை திறந்திருக்கும்.",
                'ta_latin': "Curator's Cafe 2nd floor-la iruku, 5 PM varaikkum open-la irukkum.",
                'pa_native': "ਕਿਊਰੇਟਰ ਦਾ ਕੈਫੇ ਦੂਜੀ ਮੰਜ਼ਿਲ 'ਤੇ ਹੈ, ਸ਼ਾਮ 5 ਵਜੇ ਤੱਕ ਖੁੱਲ੍ਹਾ ਰਹਿੰਦਾ ਹੈ।",
                'pa_latin': "Curator's Cafe 2nd floor te hai, shyam 5 baje tak khulla rehnda hai."
            },
            'security': {
                'en': "Security is our priority with 24/7 CCTV and entry screening.",
                'hi_native': "सुरक्षा हमारी प्राथमिकता है। 24/7 सीसीटीवी और प्रवेश जांच उपलब्ध है।",
                'hi_latin': "Security hamari priority hai. 24/7 CCTV aur screening available hai.",
                'ta_native': "பாதுகாப்பிற்கு முன்னுரிமை அளிக்கப்படுகிறது, 24/7 சிசிடிவி கண்காணிப்பு உள்ளது.",
                'ta_latin': "Security mukkusu. 24/7 CCTV surveillance iruku.",
                'pa_native': "ਸੁਰੱਖਿਆ ਸਾਡੀ ਤਜੀਹ ਹੈ, 24/7 ਸੀਸੀਟੀਵੀ ਨਿਗਰਾਨੀ ਉਪਲਬਧ ਹੈ।",
                'pa_latin': "Security sadi priority hai, 24/7 CCTV surveillance hai."
            },
            'unknown': {
                'en': "I'm not sure about that. Try asking about 'exhibitions', 'hours', or 'tickets'!",
                'hi_native': "क्षमा करें, मुझे समझ नहीं आया। क्या आप 'टिकट' या 'समय' के बारे में पूछ सकते हैं?",
                'hi_latin': "Thoda clear karenge? Aap mujhse 'tickets' ya 'timings' ke bare mein puch sakte hain.",
                'ta_native': "என்னிடம் டிக்கெட்டுகள் அல்லது நேரங்களைப் பற்றி கேளுங்கள்!",
                'ta_latin': "Puriyala. Tickets illa hours pathi kelunga.",
                'pa_native': "ਮੈਨੂੰ ਸਮਝ ਨਹੀਂ ਆਈ। ਟਿਕਟਾਂ ਜਾਂ ਸਮੇਂ ਬਾਰੇ ਪੁੱਛੋ!",
                'pa_latin': "Samajh nai aayi. Tickets ya timings baare pucho."
            }
        }
        
        # Keep greeting map for very fast singular word detection
        self.greeting_map = {
            "hello": ("greeting", "en"),
            "hi": ("greeting", "en"),
            "hey": ("greeting", "en"),
            "good morning": ("greeting", "en"),
            "namaste": ("greeting", "hi"),
            "namaskar": ("greeting", "hi"),
            "vanakkam": ("greeting", "ta"),
            "namaskaram": ("greeting", "ml"),
            "namaskara": ("greeting", "kn"), 
            "nomoskar": ("greeting", "bn"),
            "sat sri akal": ("greeting", "pa"),
            "aadab": ("greeting", "ur")
        }

    def _initialize_ai(self):
        """Performs a smoke test to select the best available Gemini model."""
        if not self.api_key:
            return
            
        try:
            self.client = genai.Client(api_key=self.api_key)
            for base_model_name in MODEL_PRIORITY:
                # Try both the bare name and the "models/" prefixed name
                for model_name in [base_model_name, f"models/{base_model_name}"]:
                    try:
                        # Small delay to avoid triggering 429s during rapid-fire smoke tests
                        time.sleep(2)
                        print(f"DEBUG: Attempting smoke test for {model_name}...")
                        # Smoke Test: Single-token generation verifies API access and model existence
                        self.client.models.generate_content(
                            model=model_name,
                            contents="ping",
                            config=types.GenerateContentConfig(max_output_tokens=1)
                        )
                        
                        self.model_id = model_name
                        print(f"SUCCESS: Verified and selected AI Model: {model_name}")
                        return # Successfully found a model
                    except Exception as e:
                        print(f"DEBUG: Model {model_name} failed smoke test. Error: {str(e)}")
                        if "401" in str(e) or "API_KEY_INVALID" in str(e):
                            print("CRITICAL: Your GEMINI_API_KEY appears to be invalid!")
                            break # No point trying other variations of this model
                        continue
            
            print("ERROR: All prioritized AI models failed verification. System using fallback mode.")
            self.client = None # Reset if no models worked
        except Exception as e:
            print(f"CRITICAL: AI configuration failure during startup: {e}")
            import traceback
            traceback.print_exc()
            self.client = None


    def _get_system_instructions(self, locked_lang, locked_script):
        """Returns the precision Museum Assistant persona with strict intent-based formatting."""
        return f"""You are a professional AI Museum Assistant. Your goal is to provide clear, structured, and easy-to-read answers.

STRICT RULES (Apply to EVERY response):
1. NO MARKDOWN: Do NOT use **bold**, ## headers, or *italics*. Use plain text ONLY.
2. NO GREETINGS: Do NOT start with "Namaste", "Hello", or "Hi". Go directly to the answer.
3. NO LONG PARAGRAPHS: Keep text concise and sentences short.
4. SPACING: Always add a blank line between every section.
5. BULLETS: Use dash-based bullet points (-) for all lists.
6. TITLE: Start with the main topic name as a plain text title on the first line.

RESPONSE STRUCTURES (Choose based on question type):

IF DEFINITION / "WHAT IS":
[Topic Name]

[Short 2-3 line explanation]

Key Features:
- Point 1
- Point 2
- Point 3

Summary:
[1-2 line conclusion]

IF "EXPLAIN IN DETAIL":
[Topic Name]

[Short introduction]

Details:
- Point 1 with short explanation
- Point 2 with short explanation
- Point 3 with short explanation

Examples (if applicable):
- Example 1
- Example 2

Summary:
[Short conclusion]

IF PLACE / MUSEUM:
[Place Name]

[Short description]

Highlights:
- Feature 1
- Feature 2

Visitor Info:
- Timings
- Tickets
- Location

Summary:
[Short closing line]

IF COMPARISON:
[Topic Comparison]

[Short intro]

Differences:
- Point 1
- Point 2

Summary:
[Conclusion]

STRICT RULES:
1. Handle museum-related queries (History, Culture, Art, Exhibits).
2. If unrelated, politely redirect to museum services.
3. [TECHNICAL] If booking tickets, include '[INIT_BOOKING]' at the VERY END.

MULTILINGUAL SUPPORT & SESSION LOCK:
* Respond in: {locked_lang} (Script: {locked_script})
* Do NOT translate labels like "Key Features:", "Summary:", "Details:", "Visitor Info:", "Highlights:" if the user is using English. Translate them appropriately if the session is locked to a regional language."""

    def _translate_to_en(self, text):
        # Basic cleanup
        text = text.strip()
        if not text:
            return text, 'en'
        
        # Don't translate very short strings or pure numbers
        if len(text) < 4 or text.isdigit():
            return text, 'en'
            
        try:
            detected = detect(text)
            if detected == 'en':
                return text, 'en'
            
            # Use 'auto' to ensure it tries its best
            translated = GoogleTranslator(source='auto', target='en').translate(text)
            print(f"DEBUG: Detected {detected}, Translated: {translated}")
            return translated, detected
        except Exception as e:
            print(f"DEBUG Translation Error: {e}")
            return text, 'en'

    def _detect_script(self, text):
        # Full Unicode ranges for Indian scripts
        scripts = {
            'devanagari': re.compile(r'[\u0900-\u097F]'),
            'gurmukhi': re.compile(r'[\u0A00-\u0A7F]'),
            'gujarati': re.compile(r'[\u0A80-\u0AFF]'),
            'bengali': re.compile(r'[\u0980-\u09FF]'),
            'tamil': re.compile(r'[\u0B80-\u0BFF]'),
            'telugu': re.compile(r'[\u0C00-\u0C7F]'),
            'kannada': re.compile(r'[\u0C80-\u0CFF]'),
            'malayalam': re.compile(r'[\u0D00-\u0D7F]'),
            'odia': re.compile(r'[\u0B00-\u0B7F]')
        }
        
        for name, pattern in scripts.items():
            if pattern.search(text):
                return "native", name
        
        # ASCII/Latin check
        if any('a' <= c.lower() <= 'z' for c in text):
            return "latin", "english"
            
        return "unknown", "unknown"

    def _detect_dominant_language(self, text):
        text_lower = text.lower()
        
        # Exact whitelist for English greetings to avoid 'hi' (Hindi code) collision
        english_greetings = ["hello", "hi", "hey", "good morning", "morning"]
        if any(w == text_lower or text_lower.startswith(w + " ") for w in english_greetings):
            return "en"
            
        # Regional overrides for Roman script greetings
        if "vanakkam" in text_lower: return "ta"
        if "sat sri akal" in text_lower: return "pa"
        if "nomoskar" in text_lower: return "bn"
        if "namaskaram" in text_lower: return "ml"
        if "namaskara" in text_lower: return "kn"
        
        # Ambiguous words: If mixed with English, prioritize English
        if "namaste" in text_lower or "namaskar" in text_lower:
            if any(w in text_lower for w in english_greetings):
                return "en"
            # Default for just "namaste" is Hindi if no other clues
            if text_lower in ["namaste", "namaskar"]:
                return "hi"

        hindi_keywords = ["mujhe", "chahiye", "kitna", "kaise", "kya", "hai", "karna", "ticket", "namaste", "shubh"]
        tamil_keywords = ["venum", "enakku", "epadi", "irukinga", "vanakkam", "nanri"]
        punjabi_keywords = ["mainu", "chahida", "kithe", "ki", "sat sri akal", "tuhanu"]
        bengali_keywords = ["nomoskar", "bhalo", "lagbe"]
        telugu_keywords = ["naaku", "kavali", "namaste", "ela"]
        kannada_keywords = ["nanage", "beku", "namaskara"]
        malayalam_keywords = ["enikku", "venam", "namaskaram"]
        gujarati_keywords = ["mane", "joie", "kem", "cho"]
        marathi_keywords = ["mala", "pahije", "kashi"]
        
        scores = {
            "hi": sum(1 for w in hindi_keywords if w in text_lower),
            "ta": sum(1 for w in tamil_keywords if w in text_lower),
            "pa": sum(1 for w in punjabi_keywords if w in text_lower),
            "bn": sum(1 for w in bengali_keywords if w in text_lower),
            "te": sum(1 for w in telugu_keywords if w in text_lower),
            "kn": sum(1 for w in kannada_keywords if w in text_lower),
            "ml": sum(1 for w in malayalam_keywords if w in text_lower),
            "gu": sum(1 for w in gujarati_keywords if w in text_lower),
            "mr": sum(1 for w in marathi_keywords if w in text_lower)
        }
        
        # If no keywords found, default to hi as it's the most likely Hinglish variant
        # but only if total score is > 0, otherwise let langdetect handle baseline
        if sum(scores.values()) == 0:
            return None
            
        return max(scores, key=scores.get)

    def _enforce_script(self, response, script_type):
        """Ensures the response doesn't contain the wrong block of characters."""
        if script_type == "latin":
            # Strip any native script characters that might have sneaked in
            # This is a safety layer to preserve 100% script consistency
            return re.sub(r'[^\x00-\x7F]+', '', response)
        return response

    def _get_localized_response(self, template_key, user_lang, user_script_data, **kwargs):
        """Retrieves a response from templates or translates as fallback."""
        user_script, script_name = user_script_data
        
        if template_key in self.templates:
            # Construction of searching hierarchy
            if user_lang == 'en':
                # Special priority for English
                search_keys = ['en', 'hi_latin', 'hi_native']
            else:
                search_keys = [
                    f"{user_lang}_{user_script}",  # e.g., 'ta_latin'
                    f"{user_lang}_native",         # e.g., 'ta_native'
                    f"hi_{user_script}",          # fallback to Hindi/Hinglish
                    "hi_native",                   # fallback to Hindi
                    "en"                           # final fallback
                ]
            
            final_key = "en"
            for k in search_keys:
                if k in self.templates[template_key]:
                    final_key = k
                    break
            
            resp = self.templates[template_key].get(final_key)
            formatted_resp = resp.format(**kwargs)
            return self._enforce_script(formatted_resp, user_script)
        
        # True Fallback: Dynamic Translation
        raw_translation = self._translate_from_en(template_key, user_lang)
        return self._enforce_script(raw_translation, user_script)

    def _translate_from_en(self, text, target_lang):
        try:
            if not target_lang or target_lang == 'en':
                return text
            
            # Map common ISO codes for deep-translator if needed, 
            # though GoogleTranslator usually handles standard ones.
            translated = GoogleTranslator(source='en', target=target_lang).translate(text)
            return translated
        except Exception as e:
            print(f"DEBUG Back-Translation Error: {e}")
            return text

    def process_message(self, message, state_data):
        state = state_data.get('state', 'idle')
        
        # 0. High-Fidelity Normalization (Production Grade)
        clean_msg = re.sub(r'[^\w\s]', '', message.lower()).strip()
        clean_msg = re.sub(r'\s+', ' ', clean_msg)

        # 1. Session-Based Language & Script Locking
        locked_lang = state_data.get('locked_lang')
        locked_script = state_data.get('locked_script')
        
        user_script_data = self._detect_script(message)
        user_script, script_name = user_script_data
        
        # Initial detection
        dominant_lang = self._detect_dominant_language(clean_msg)
        translated_msg, detected_lang = self._translate_to_en(message)
        current_input_lang = dominant_lang if dominant_lang and user_script == 'latin' else detected_lang

        # 2. Fast-Path Greeting Logic - Word-boundary specific
        # We check all matching greetings and prefer the one that matches our detected current_input_lang
        matches = []
        for key, (template_key, lang_hint) in self.greeting_map.items():
            if re.search(fr'\b{key}\b', clean_msg):
                matches.append((key, template_key, lang_hint))
        
        if matches:
            # Sort by priority: 1. Matches current_input_lang, 2. Longest key (most specific)
            matches.sort(key=lambda x: (x[2] != current_input_lang, -len(x[0])))
            key, template_key, lang_hint = matches[0]
                
            # UPDATED: We ALWAYS set/update the session lock based on a greeting.
            # This allows the user to "switch" languages by greeting the bot.
            locked_lang = lang_hint
            locked_script = user_script
            state_data['locked_lang'] = locked_lang
            state_data['locked_script'] = locked_script
            
            # Use the greeting's intrinsic lang_hint for the response itself
            return self._get_localized_response(template_key, lang_hint, (locked_script, locked_script)), state_data

        # 1. Session-Based Language & Script Locking (after greeting check)
        if not locked_lang:
            locked_lang = current_input_lang
            locked_script = user_script
            state_data['locked_lang'] = locked_lang
            state_data['locked_script'] = locked_script
        
        # Use locked values for all subsequent responses
        user_lang = locked_lang
        final_script_data = (locked_script, script_name)
        msg_lower = translated_msg.lower()

        # 1. Handle Numerical State Transitions (Selection & Count)
        if state == 'awaiting_exhibition_selection':
            match = re.search(r'\b\d+\b', translated_msg)
            if match:
                ex_id = int(match.group())
                conn = get_db_connection()
                exhibition = conn.execute('SELECT * FROM exhibitions WHERE id = ?', (ex_id,)).fetchone()
                conn.close()
                if exhibition:
                    state_data['exhibition'] = dict(exhibition)
                    state_data['state'] = 'awaiting_ticket_count'
                    return self._get_localized_response('ticket_count', user_lang, final_script_data, title=exhibition['title']), state_data

        elif state == 'awaiting_ticket_count':
            match = re.search(r'\b\d+\b', translated_msg)
            if match:
                count = int(match.group())
                if count > 0:
                    state_data['count'] = count
                    state_data['state'] = 'awaiting_payment_confirm'
                    total = count * state_data['exhibition']['price']
                    state_data['total'] = total
                    
                    # We keep the button HTML as is since it has specific function calls
                    confirm_text = self._get_localized_response('payment_confirm', user_lang, final_script_data, 
                                                                count=count, title=state_data['exhibition']['title'], total=total)
                    btn_html = f"<div style='margin-top:10px;'><button class='cta-btn' onclick='openPaymentModal({total})'>Proceed to Ledger (₹{total})</button></div>"
                    return f"{confirm_text}<br>{btn_html}", state_data

        # 2. Generative AI Logic with 429 Resilience
        if self.client and self.model_id:
            for attempt in range(MAX_RETRIES + 1):
                try:
                    instructions = self._get_system_instructions(user_lang, user_script)
                    # Pass strict context without full history to save tokens/cost
                    prompt = f"SESSION_LANG: {user_lang}\nSESSION_SCRIPT: {user_script}\nINSTRUCTIONS: {instructions}\nUSER: {message}"
                    
                    response = self.client.models.generate_content(
                        model=self.model_id,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            max_output_tokens=MAX_TOKENS,
                            temperature=0.7
                        )
                    )
                    
                    ai_text = response.text
                    
                    # Post-processing to enforce "No Markdown Symbols" rule
                    # 1. Remove bolding (**text** or __text__)
                    ai_text = re.sub(r'\*\*(.*?)\*\*', r'\1', ai_text)
                    ai_text = re.sub(r'__(.*?)__', r'\1', ai_text)
                    # 2. Remove all asterisks (italics or bold remnants)
                    ai_text = re.sub(r'\*', '', ai_text)
                    # 3. Remove heading symbols (### Header)
                    ai_text = re.sub(r'#+\s*(.*)', r'\1', ai_text)
                    
                    # Final script enforcement and cleanup
                    ai_text = self._enforce_script(ai_text, user_script).strip()
                    
                    if self.booking_marker in ai_text:
                        ai_text = ai_text.replace(self.booking_marker, "").strip()
                        state_data['state'] = 'awaiting_exhibition_selection'
                    
                    if any(word in message.lower() for word in ['cancel', 'stop', 'restart']):
                        state_data['state'] = 'idle'

                    return ai_text, state_data

                except Exception as e:
                    error_msg = str(e)
                    is_quota_error = any(code in error_msg for code in ["429", "ResourceExhausted", "Quota exceeded"])
                    
                    if is_quota_error:
                        print(f"WARNING: Rate limit exceeded (429). Attempt {attempt+1}/{MAX_RETRIES+1}")
                        if attempt < MAX_RETRIES:
                            # Try to extract retry delay from exception if available
                            wait_time = DEFAULT_RETRY_DELAY
                            match = re.search(r'retry in (\d+\.?\d*)s', error_msg)
                            if match:
                                wait_time = float(match.group(1))
                            
                            time.sleep(wait_time)
                            continue
                    
                    print(f"ERROR: AI Generation failure: {error_msg}")
                    break # Exit loop and hit fallback brain
        
        # --- BACKUP BRAIN (Enhanced Multilingual Fallback) ---
            
        # Greetings
        if re.search(r'\b(hi|hello|hey|namaste|greetings|pranam|aadab|shubh)\b', msg_lower):
            return self._get_localized_response('greeting', user_lang, final_script_data), state_data
        
        # Booking
        if re.search(r'\b(book|ticket|buy|reserve|yatra|ticketen)\b', msg_lower):
            state_data['state'] = 'awaiting_exhibition_selection'
            conn = get_db_connection()
            exhibs = conn.execute('SELECT * FROM exhibitions').fetchall()
            conn.close()
            translated_resp = self._get_localized_response('booking_start', user_lang, final_script_data)
            for e in exhibs: 
                translated_resp += f"<b>{e['id']}. {e['title']}</b> - ₹{e['price']}<br>"
            return translated_resp, state_data
            
        # Quick Info
        if 'hour' in msg_lower or 'time' in msg_lower or 'open' in msg_lower:
            return self._get_localized_response('hours', user_lang, final_script_data), state_data
        if 'park' in msg_lower or 'car' in msg_lower or 'vehic' in msg_lower:
            return self._get_localized_response('parking', user_lang, final_script_data), state_data
        if 'cafe' in msg_lower or 'food' in msg_lower or 'eat' in msg_lower or 'restaur' in msg_lower:
            return self._get_localized_response('cafe', user_lang, final_script_data), state_data
        if 'secur' in msg_lower or 'safe' in msg_lower:
            return self._get_localized_response('security', user_lang, final_script_data), state_data
        
        # Museum Info / About
        if 'museum' in msg_lower or 'best' in msg_lower or 'about' in msg_lower or 'explore' in msg_lower:
            return "This Museum is one of India's finest, showcasing our rich heritage and art. We have amazing exhibitions and a great cafe! Try asking 'what exhibitions do you have?'", state_data
        
        return self._get_localized_response('unknown', user_lang, final_script_data), state_data

    def process_payment_success(self, state_data, user_id):
        ticket_hash = str(uuid.uuid4())[:8].upper()
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO bookings (user_id, visitor_name, exhibition_id, num_tickets, total_price, ticket_hash) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, 'Heritage Guest', state_data['exhibition']['id'], state_data['count'], state_data['total'], ticket_hash)
        )
        conn.commit()
        conn.close()
        
        state_data['state'] = 'idle'
        return {'success': True, 'chat_message': f"Payment Successful! 🎉<br>Booking ID: {ticket_hash}<br>Enjoy your visit to the museum!"}, state_data
