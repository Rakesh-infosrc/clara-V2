"""Utility helpers for multilingual support and code-mixed transcripts."""
from __future__ import annotations

import string
from typing import Dict, Iterable, List

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en", "ta", "te", "hi"}

LANGUAGE_CODE_ALIASES: Dict[str, str] = {
    "en": "en",
    "eng": "en",
    "en-us": "en",
    "en-in": "en",
    "english": "en",
    "tamil": "ta",
    "telugu": "te",
    "hindi": "hi",
    "ta": "ta",
    "tam": "ta",
    "ta-in": "ta",
    "te": "te",
    "tel": "te",
    "te-in": "te",
    "hi": "hi",
    "hin": "hi",
    "hi-in": "hi",
}

MESSAGES = {
    "wake_intro": {
        "en": "Hello, my name is Clara, the receptionist at Info Services. How may I help you today?",
        "ta": "வணக்கம், நான் கிளாரா, இன்போ சர்வீசஸ் அலுவலகத்தின் வரவேற்பாளர். இன்று நான் எப்படி உதவலாம்?",
        "te": "హలో, నేను క్లారా, ఇన్ఫో సర్వీసెస్ రిసెప్షనిస్ట్. ఈ రోజు మీకు ఎలా సహాయం చేయగలను?",
        "hi": "नमस्ते, मैं क्लारा हूँ, इन्फो सर्विसेस की रिसेप्शनिस्ट। आज मैं आपकी कैसे मदद कर सकती हूँ?",
    },
    "wake_prompt": {
        "en": "Hello! Are you an Employee or a Visitor?",
        "ta": "வணக்கம்! நீங்கள் ஊழியரா அல்லது பார்வையாளரா?",
        "te": "హలో! మీరు ఎంప్లాయీ లేదా విసిటర్నా?",
        "hi": "नमस्ते! क्या आप कर्मचारी हैं या आगंतुक?",
    },
    "language_selection_prompt": {
        "en": "I can speak English, Tamil, Telugu, and Hindi. Which one do you prefer?",
        "ta": "நான் ஆங்கிலம், தமிழ், தெலுங்கு மற்றும் இந்தி மொழிகளில் பேச முடியும். நீங்கள் எந்த மொழியை விரும்புகிறீர்கள்?",
        "te": "నేను ఇంగ్లీష్, తమిళం, తెలుగు, హిందీ మాట్లాడగలను. మీరు ఏ భాషలో మాట్లాడాలని ఇష్టపడుతున్నారు?",
        "hi": "मैं अंग्रेज़ी, तमिल, तेलुगु और हिंदी में बात कर सकती हूँ। आप किस भाषा को पसंद करते हैं?",
    },
    "language_selection_retry": {
        "en": "Please say English, Tamil, Telugu, or Hindi so I can continue.",
        "ta": "தயவுசெய்து ஆங்கிலம், தமிழ், தெலுங்கு அல்லது இந்தி என்று கூறுங்கள்.",
        "te": "దయచేసి ఇంగ్లీష్, తమిళం, తెలుగు, లేదా హిందీలో చెప్పండి, అప్పుడు నేను కంటిన్యూ చేయగలను.",
        "hi": "कृपया अंग्रेज़ी, तमिल, तेलुगु या हिंदी में से किसी एक का नाम बताइए।",
    },
    "language_selection_confirmed": {
        "en": "Great! I'll speak in English. Are you an Employee or a Visitor?",
        "ta": "சிறப்பு! நான் தமிழ் மொழியில் பேசுகிறேன். நீங்கள் ஊழியரா அல்லது பார்வையாளரா?\n(English) I'll speak Tamil. Are you an Employee or a Visitor?",
        "te": "గ్రేట్! నేను తెలుగు మాట్లాడతాను. మీరు ఎంప్లాయీ లేదా విసిటర్?\n(English) I'll speak Telugu. Are you an Employee or a Visitor?",
        "hi": "बहुत बढ़िया! मैं हिंदी में बात करूँगी। क्या आप कर्मचारी हैं या आगंतुक?\n(English) I'll speak Hindi. Are you an Employee or a Visitor?",
    },
    "classification_employee": {
        "en": "Great! Please tap the Employee Mode button, then look at the camera for verification.",
        "ta": "சிறப்பாக இருக்கிறது! Employee Mode பொத்தானை தட்டி, பின்னர் சரிபார்ப்புக்காக கேமராவை நோக்கிப் பாருங்கள்.",
        "te": "గ్రేట్! దయచేసి ఎంప్లాయీ మోడ్ బటన్‌ను ట్యాప్ చేసి, వెరిఫికేషన్ కోసం కెమెరా వైపు చూడండి.",
        "hi": "बहुत बढ़िया! कृपया Employee Mode बटन टैप करें और फिर सत्यापन के लिए कैमरे की ओर देखें।",
    },
    "classification_visitor": {
        "en": "Welcome! Please provide your name, phone number, purpose of visit, and who you're meeting.",
        "ta": "வரவேற்கிறோம்! உங்கள் பெயர், தொலைபேசி எண், வருகையின் காரணம், மேலும் யாரை சந்திக்கிறீர்கள் என்பதை கூறுங்கள்.",
        "te": "వెల్కమ్! దయచేసి మీ వివరాలు చెప్పండి: పేరు, ఫోన్ నంబర్, విసిట్ పర్పస్, మరియు మీరు కలుసుకోవబోయే వ్యక్తి.",
        "hi": "स्वागत है! कृपया अपना नाम, फ़ोन नंबर, आने का उद्देश्य और किससे मिलने आए हैं बताइए।",
    },
    "flow_face_recognition_prompt": {
        "en": "Tap the Employee Mode button and face the camera so I can start your verification.",
        "ta": "Employee Mode பொத்தானை தட்டி, சரிபார்ப்பைத் தொடங்க நான் கேமராவை நோக்கிப் பாருங்கள்.",
        "te": "మీ వెరిఫికేషన్ను ప్రారంభించేందుకు ఎంప్లాయీ మోడ్ బటన్‌ను ట్యాప్ చేసి కెమెరా వైపు చూడండి.",
        "hi": "कृपया Employee Mode बटन टैप करके कैमरे की ओर देखें ताकि मैं आपका सत्यापन शुरू कर सकूँ।",
    },
    "flow_manual_verification_prompt": {
        "en": "Please share your name and employee ID. If you received an OTP, tell me now.",
        "ta": "தயவுசெய்து உங்கள் பெயர் மற்றும் ஊழியர் அடையாள எண்ணை கூறுங்கள். OTP கிடைத்திருந்தால் இப்போது சொல்லுங்கள்.",
        "te": "దయచేసి మీ పేరు మరియు ఎంప్లాయీ ID చెప్పండి. మీరు OTP పొందితే, ఇప్పుడు చెప్పండి.",
        "hi": "कृपया अपना नाम और कर्मचारी आईडी बताइए। यदि आपको ओटीपी मिला है तो अभी बताइए।",
    },
    # "flow_credential_check_prompt": {
    #     "en": "Would you like me to register your face for faster access next time?",
    #     "ta": "அடுத்த முறை வேகமான அணுகலுக்காக உங்கள் முகத்தை பதிவு செய்ய விரும்புகிறீர்களா?",
    #     "te": " వేగంగా ప్రవేశించడానికి మీ ముఖాన్ని రిజిస్టర్ చేయాలని మీరు కోరుకుంటున్నారా?",
    #     "hi": "क्या आप अगली बार तेज़ प्रवेश के लिए अपना चेहरा पंजीकृत कराना चाहेंगे?",
    # },
    "flow_face_registration_prompt": {
        "en": "Hold still and look at the camera — capturing your face now.",
        "ta": "அசையாமல் கேமராவை நோக்கிப் பாருங்கள் — உங்கள் முகத்தை இப்போது பதிவு செய்கிறேன்.",
        "te": "అలానే ఉండండి, ముఖం చూపండి — ఇప్పుడు మీ ముఖాన్ని క్యాప్చర్ చేస్తున్నారు.",
        "hi": "स्थिर रहें और कैमरे की ओर देखें — मैं अभी आपका चेहरा कैप्चर कर रही हूँ।",
    },
    "flow_employee_verified_prompt": {
        "en": "You are all set. How may I assist you today?",
        "ta": "நீங்கள் தயார். இன்று எப்படி உதவலாம்?",
        "te": "మీ అన్ని ఏర్పాట్లు పూర్తయ్యాయి. నేను ఈ రోజు ఎలా సహాయం చేయగలను?",
        "hi": "सब तैयार है। आज मैं आपकी कैसे मदद कर सकती हूँ?",
    },
    "flow_visitor_info_prompt": {
        "en": "Please tell me your name, phone number, purpose of visit, and whom you are meeting.",
        "ta": "தயவுசெய்து உங்கள் பெயர், தொலைபேசி எண், வருகையின் காரணம் மற்றும் யாரை சந்திக்கிறீர்கள் என்பதை கூறுங்கள்.",
        "te": "దయచేసి మీ పేరు, ఫోన్ నంబర్, విసిట్ పర్పస్ మరియు మీరు ఎవరిని కలవబోతున్నారో చెప్పండి.",
        "hi": "कृपया अपना नाम, फ़ोन नंबर, आने का उद्देश्य और आप किससे मिलने आए हैं बताइए।",
    },
    "flow_visitor_face_capture_prompt": {
        "en": "Please look at the camera so I can capture your photo for the visitor log.",
        "ta": "நான் பார்வையாளர் பதிவுக்காக உங்கள் புகைப்படத்தை பிடிக்க கேமராவை நோக்கிப் பாருங்கள்.",
        "te": "దయచేసి ముఖం చూపండి, నేను విసిటర్ రిజిస్టర్ కోసం మీ ఫోటోని క్యాప్చర్ చేయగలను.",
        "hi": "कृपया कैमरे की ओर देखें ताकि मैं आगंतुक रजिस्टर के लिए आपका फोटो ले सकूँ।",
    },
    "visitor_need_name": {
        "en": "Please tell me your name so I can log your visit.",
        "ta": "தயவுசெய்து உங்கள் வருகையை பதிவு செய்ய உங்கள் பெயரை கூறுங்கள்.",
        "te": "దయచేసి మీ పేరు చెప్పండి, మీ విసిట్ నమోదు చేయగలను.",
        "hi": "कृपया आपका नाम बताइए ताकि मैं आपकी विज़िट दर्ज कर सकूँ।",
    },
    "visitor_need_phone": {
        "en": "Please share your phone number so I can complete the log.",
        "ta": "பதிவை முடிக்க உங்கள் தொலைபேசி எண்ணை பகிரவும்.",
        "te": "దయచేసి మీ ఫోన్ నంబర్ చెప్పండి, లాగ్ పూర్తి చేయడానికి.",
        "hi": "कृपया आपका फ़ोन नंबर साझा कीजिए ताकि मैं रिकॉर्ड पूरा कर सकूँ।",
    },
    "visitor_need_purpose": {
        "en": "Please let me know the purpose of your visit.",
        "ta": "உங்கள் வருகையின் காரணத்தை தெரியப்படுத்துங்கள்.",
        "te": "దయచేసి మీ విసిట్ పర్పస్ చెప్పండి.",
        "hi": "कृपया अपनी विज़िट का उद्देश्य बताइए।",
    },
    "visitor_need_host": {
        "en": "Please tell me whom you are visiting so I can notify them.",
        "ta": "நீங்கள் சந்திக்க விரும்பும் நபரின் பெயரை கூறுங்கள் ताकि நான் அவர்களுக்கு தெரிவிக்க முடியும்.",
        "te": "దయచేసి మీరు ఎవరిని కలుసుకోవడానికి వచ్చారో చెప్పండి, అప్పుడు వారిని తెలియజేయగలను.",
        "hi": "कृपया बताइए आप किससे मिलने आए हैं ताकि मैं उन्हें सूचित कर सकूँ।",
    },
    "visitor_photo_prompt": {
        "en": "Thank you! I've logged your visit and notified {host}. Please look at the camera so we can capture your photo for our visitor log.",
        "ta": "நன்றி! உங்கள் வருகையை பதிவு செய்து {host} அவர்களுக்கு தெரிவித்து விட்டேன். பார்வையாளர் பதிவிற்காக தயவுசெய்து கேமராவை நோக்கிப் பாருங்கள்.",
        "te": "ధన్యవాదాలు! మీ విసిట్ నమోదు చేసి {host}కు తెలియజేశాను. దయచేసి ముఖం చూపండి, మాకు విసిట్ లాగ్ కోసం మీ ఫోటోను తీసుకోవడానికి.",
        "hi": "धन्यवाद! मैंने आपकी विज़िट दर्ज करके {host} को सूचित कर दिया है। कृपया कैमरे की ओर देखें ताकि हम आगंतुक रजिस्टर के लिए आपकी फोटो ले सकें।",
    },
    "flow_host_notification_prompt": {
        "en": "I have informed your host. Please wait at the reception.",
        "ta": "உங்கள் வரவேற்பாளருக்கு நான் தகவல் தெரிவித்துள்ளேன். தயவுசெய்து வரவேற்பில் காத்திருக்கவும்.",
        "te": "నేను మీ హోస్ట్‌కి తెలియజేసాను. దయచేసి రిసెప్షన్ వద్ద వేచి ఉండండి.",
        "hi": "मैंने आपके मेजबान को सूचित कर दिया है। कृपया रिसेप्शन पर प्रतीक्षा करें।",
    },
    "flow_end_prompt": {
        "en": "Thank you. If you need anything else, just say 'Hey Clara'.",
        "ta": "நன்றி. இன்னும் ஏதேனும் தேவையெனில் 'Hey Clara' என்று சொல்லுங்கள்.",
        "te": "ధన్యవాదాలు. మీకు ఇంకేమైనా కావాలంటే, కేవలం 'Hey Clsra' అని చెప్పండి.",
        "hi": "धन्यवाद। यदि आपको और कुछ चाहिए तो 'Hey Clara' कह दीजिए।",
    },
    "language_support_affirm": {
        "en": "I can assist you in English, Tamil, Telugu, or Hindi. How may I help you?",
        "ta": "நான் ஆங்கிலம், தமிழ், தெலுங்கு, இந்தி மொழிகளில் உதவ முடியும். எப்படி உதவலாம்?",
        "te": "నేను మీకు ఇంగ్లీష్, తమిళం, తెలుగు, లేదా హిందీలో సహాయం చేయగలను. నేను మీకు ఎలా సహాయం చేయగలను?",
        "hi": "मैं अंग्रेज़ी, तमिल, तेलुगु या हिंदी में आपकी मदद कर सकती हूँ। मैं आपकी कैसे सहायता करूँ?",
    },
    "manual_face_not_recognized": {
        "en": "Face not recognized. Please share your registered company email or employee ID so I can verify you manually.",
        "ta": "முகம் கண்டறியப்படவில்லை. கையேட்டு சரிபார்ப்புக்காக தயவுசெய்து உங்கள் பதிவு செய்யப்பட்ட நிறுவன மின்னஞ்சல் அல்லது ஊழியர் ஐடி அளிக்கவும்.",
        "te": "ముఖం గుర్తించబడలేదు. దయచేసి మీ రిజిస్టర్ అయిన కంపెనీ ఇమెయిల్ లేదా ఎంప్లాయీ ID చెప్పండి, అప్పుడు నేను మాన్యువల్‌గా మీను పరిశీలించగలను.",
        "hi": "चेहरा पहचाना नहीं जा सका। कृपया मैनुअल सत्यापन के लिए अपना पंजीकृत कंपनी ईमेल या कर्मचारी आईडी बताइए।",
    },
    "manual_no_session": {
        "en": "No active session. Please say 'Hey Clara' to start.",
        "ta": "செயலில் இருக்கும் அமர்வு இல்லை. தொடங்க 'Hey Clara' என்று சொல்லுங்கள்.",
        "te": "యాక్టివ్ సెషన్ లేదు. ప్రారంభించడానికి 'హే క్లారా' అని చెప్పండి.",
        "hi": "कोई सक्रिय सत्र नहीं है। प्रारंभ करने के लिए 'Hey Clara' कहिए।",
    },
    "manual_missing_employee_id": {
        "en": "Please provide your employee ID so I can message you on Teams.",
        "ta": "உங்கள் ஊழியர் ஐடியைத் தெரிவிக்கவும், அதனால் நான் Teams-ல் உங்களை தொடர்பு கொள்ள முடியும்.",
        "te": "దయచేసి మీ ఎంప్లాయీ ID ఇవ్వండి, అప్పుడు నేను Teams లో మీకు మెసేజ్ చేయగలను.",
        "hi": "कृपया अपना कर्मचारी आईडी बताइए ताकि मैं आपको Teams पर संदेश भेज सकूँ।",
    },
    "manual_prompt_company_email": {
        "en": "I’ll verify your details and send an OTP via Teams. Please share it once you receive the message.",
        "ta": "நான் உங்கள் விவரங்களைச் சரிபார்த்து Teams மூலம் OTP அனுப்புகிறேன். அது வந்தவுடன் எனக்குச் சொல்லுங்கள்.",
        "te": "నేను మీ వివరాలను పరిశీలించి Teams ద్వారా OTP పంపిస్తాను. దయచేసి మీరు మెసేజ్ పొందిన తర్వాత అది షేర్ చేయండి.",
        "hi": "मैं आपकी जानकारी की पुष्टि करके Teams पर ओटीपी भेजूँगी। उसे मिलते ही मुझे बताइए।",
    },
    "manual_preparation_error": {
        "en": "I couldn’t prepare verification because of an internal error ({error}). Please try again.",
        "ta": "உள் பிழை ({error}) காரணமாக சரிபார்ப்பை தயார் செய்ய முடியவில்லை. தயவுசெய்து மறுபடியும் முயற்சிக்கவும்.",
        "te": "ఇంటర్నల్ ఎరర్ ({error}) కారణంగా వేరిఫికేషన్ సిద్ధం చేయలేకపోయాను. దయచేసి మళ్ళీ ప్రయత్నించండి.",
        "hi": "आंतरिक त्रुटि ({error}) की वजह से सत्यापन तैयार नहीं कर पाई। कृपया दोबारा प्रयास करें।",
    },
    "manual_internal_error_retry": {
        "en": "I ran into an internal error during verification. Could you please share the OTP again?",
        "ta": "சரிபார்ப்பின் போது உள் பிழை ஏற்பட்டது. தயவுசெய்து OTP-ஐ மீண்டும் தெரிவிக்க முடியுமா?",
        "te": "వేరిఫికేషన్ సమయంలో ఇంటర్నల్ ఎరర్ వచ్చింది. దయచేసి OTPను మళ్లీ షేర్ చేయగలరా?",
        "hi": "सत्यापन के दौरान आंतरिक त्रुटि हुई। कृपया ओटीपी फिर से बताएँ।",
    },
    "manual_credentials_verified": {
        "en": "Credentials verified! Would you like to register your face for faster access next time? (Yes or No)",
        "ta": "சரிபார்ப்பு வெற்றிகரமாக முடிந்தது! அடுத்த முறை விரைவாக அணுக முகம் பதிவு செய்ய விரும்புகிறீர்களா? (ஆம்/இல்லை)",
        "te": "క్రెడెన్షియల్స్ వెరిఫై అయ్యిది! తదుపరి సులభమైన ప్రవేశం కోసం మీ ముఖాన్ని రిజిస్టర్ చేయాలా? (అవును లేదా కాదు)",
        "hi": "सत्यापन सफल हो गया! अगली बार तेज़ प्रवेश के लिए क्या आप अपना चेहरा पंजीकृत कराना चाहेंगे? (हाँ/नहीं)",
    },
    "manual_otp_failed": {
        "en": "OTP verification failed. Please request a new OTP or try again.",
        "ta": "OTP சரிபார்ப்பு தோல்வியடைந்தது. புதிய OTP-ஐ கோருங்கள் அல்லது மீண்டும் முயற்சிக்கவும்.",
        "te": "OTP వెరిఫికేషన్ ఫెయిల్ అయిది. దయచేసి కొత్త OTPని రిక్వెస్ట్ చేయండి లేదా మళ్లీ ప్రయత్నించండి.",
        "hi": "ओटीपी सत्यापन विफल हुआ। कृपया नया ओटीपी माँगें या दोबारा प्रयास करें।",
    },
    "manual_otp_sent": {
        "en": "I’ve sent an OTP to your registered phone number via SMS. Please share it to complete verification.",
        "ta": "உங்கள் பதிவு செய்யப்பட்ட தொலைபேசி எண்ணுக்கு SMS மூலம் OTP அனுப்பியுள்ளேன். சரிபார்ப்பை நிறைவு செய்ய அதை பகிரவும்.",
        "te": "మీ నమోదిత ఫోన్ నంబర్‌కు SMS ద్వారా OTP పంపాను. వెరిఫికేషన్ పూర్తి చేయడానికి దయచేసి దాన్ని చెప్పండి.",
        "hi": "मैंने आपके पंजीकृत फोन नंबर पर SMS के माध्यम से ओटीपी भेजा है। सत्यापन पूरा करने के लिए कृपया उसे बताएं।",
    },
    "manual_otp_send_failed": {
        "en": "I couldn't send the OTP right now ({error}). Please try again shortly.",
        "ta": "இப்போது OTP அனுப்ப முடியவில்லை ({error}). சிறிது நேரத்தில் மீண்டும் முயற்சிக்கவும்.",
        "te": "ప్రస్తుతం OTP పంపలేకపోయాను ({error}). కొద్దిసేపటి తర్వాత మళ్లీ ప్రయత్నించండి.",
        "hi": "मैं फिलहाल ओटीपी भेज नहीं पाई ({error})। कृपया थोड़ी देर में फिर कोशिश करें।",
    },
    "manual_invalid_session": {
        "en": "Invalid session or user type.",
        "ta": "அமர்வு அல்லது பயனர் வகை தவறானது.",
        "te": "ఇన్వాలిడ్ సెషన్ లేదా యూజర్ టైప్.",
        "hi": "सत्र या उपयोगकर्ता प्रकार मान्य नहीं है।",
    },
    "manual_not_verified": {
        "en": "Invalid session or not verified yet.",
        "ta": "அமர்வு தவறானது அல்லது இன்னும் சரிபார்க்கப்படவில்லை.",
        "te": "ఇన్వాలిడ్ సెషన్ లేదా ఇంకా వెరిఫై కాలేదు.",
        "hi": "सत्र मान्य नहीं है या अभी सत्यापन नहीं हुआ है।",
    },
    "face_recognition_success": {
        "en": "I’m glad to see you, {name}. How can I help you today?",
        "ta": "உங்களை மீண்டும் சந்தித்ததில் மகிழ்ச்சி, {name}. இன்று எப்படி உதவலாம்?",
        "te": "మిమ్మల్ని చూసి ఆనందంగా ఉంది {name}. ఈ రోజు ఎలా సహాయం చేయగలను?",
        "hi": "आपसे मिलकर खुशी हुई, {name}। आज मैं आपकी कैसे मदद कर सकती हूँ?",
    },
    "face_registration_ready": {
        "en": "Please look at the camera to register your face for future quick access.",
        "ta": "அடுத்த முறை விரைவாக அணுக உங்கள் முகத்தை பதிவு செய்ய கேமராவை நோக்கிப் பாருங்கள்.",
        "te": "దయచేసి కెమెరా వైపు చూసి మీ ముఖాన్ని రిజిస్టర్ చేసుకోండి, ఫ్యూచర్ యాక్సెస్ కోసం.",
        "hi": "अगली बार तेज़ प्रवेश के लिए अपना चेहरा दर्ज कराने हेतु कैमरे की ओर देखें।",
    },
    "face_registration_skip_ack": {
        "en": "Perfect! You now have full access to all tools. How can I assist you today?",
        "ta": "சிறப்பானது! அனைத்து கருவிகளுக்கும் இப்போது முழு அணுகல் உங்களுக்குள்ளது. இன்று எப்படி உதவலாம்?",
        "te": "పర్ఫెక్ట్! ఇప్పుడు మీకు అన్ని టూల్స్‌కి పూర్తి యాక్సెస్ ఉంది. ఈ రోజు నేను మీకు ఎలా సహాయం చేయగలను?",
        "hi": "बहुत बढ़िया! अब आपको सभी उपकरणों का पूरा उपयोग मिल गया है। आज मैं आपकी कैसे मदद कर सकती हूँ?",
    },
    "face_registration_success": {
        "en": "Face registered in system! You now have full access to all tools. How can I assist you today?",
        "ta": "முகம் வெற்றிகரமாக பதிவுசெய்யப்பட்டது! அனைத்து கருவிகளிலும் உங்களுக்கு முழு அணுகல் உள்ளது. எப்படி உதவலாம்?",
        "te": "ముఖం సిస్టమ్‌లో రిజిస్టర్ అయింది! ఇప్పుడు మీకు అన్ని టూల్స్‌కి పూర్తి యాక్సెస్ ఉంది. ఈ రోజు నేను మీకు ఎలా సహాయం చేయగలను?",
        "hi": "चेहरा सफलतापूर्वक दर्ज हो गया! अब आपको सभी उपकरणों का पूरा उपयोग मिल गया है। मैं कैसे मदद करूँ?",
    },
    "search_prompt": {
        "en": "What would you like me to search for?",
        "ta": "எதைத் தேட வேண்டும் என்று விரும்புகிறீர்கள்?",
        "te": "నేను ఏది వెతకాలని మీరు కోరుకుంటున్నారు?",
        "hi": "आप चाहते हैं कि मैं क्या खोजूँ?",
    },
    "weather_report": {
        "en": "{city}: {report}",
        "ta": "{city}: {report}",
        "te": "{city}: {report}",
        "hi": "{city}: {report}",
    },
    "weather_error": {
        "en": "❌ Unable to retrieve the weather right now.",
        "ta": "❌ தற்போது வானிலை தகவலை பெற முடியவில்லை.",
        "te": "❌ ప్రస్తుతం వాతావరణాన్ని పొందలేకపోతున్నాము.",
        "hi": "❌ इस समय मौसम जानकारी प्राप्त नहीं कर पा रही हूँ।",
    },
    "start_face_capture": {
        "en": "Please tap the Employee Mode button to proceed.",
        "ta": "தொடர்வதற்காக Employee Mode பொத்தானை தட்டவும்.",
        "te": "కొనసాగేందుకు ఎంప్లాయీ మోడ్ బటన్‌ను ట్యాప్ చేయండి.",
        "hi": "आगे बढ़ने के लिए कृपया Employee Mode बटन टैप करें।",
    },
    "start_visitor_info": {
        "en": "Please enter your name, phone number, purpose, and who you're meeting.",
        "ta": "தயவுசெய்து உங்கள் பெயர், தொலைபேசி எண், வருகை காரணம் மற்றும் யாரை சந்திக்கிறீர்கள் என்பதை உள்ளிடுங்கள்.",
        "te": "దయచేసి మీ పేరు, ఫోన్ నంబర్, విసిట్ పర్పస్ మరియు మీరు ఎవరిని కలవబోతున్నారో నమోదు చేయండి.",
        "hi": "कृपया अपना नाम, फ़ोन नंबर, आने का उद्देश्य और किससे मिलने आए हैं दर्ज करें।",
    },
    "wake_ack": {
        "en": "I'm awake! How can I help?",
        "ta": "நான் விழித்துள்ளேன்! எப்படி உதவலாம்?",
        "te": "నేను మేలుకున్నాను! ఎలా సహాయం చేయగలను?",
        "hi": "मैं जाग गई हूँ! मैं कैसे मदद कर सकती हूँ?",
    },
    "sleep_ack": {
        "en": "Going idle, say 'Hey Clara' to wake me again.",
        "ta": "நான் ஓய்வெடுக்கிறேன், மீண்டும் எழுப்ப 'Hey Clara' என்று சொல்லுங்கள்.",
        "te": "నేను విశ్రాంతి తీసుకుంటాను, మళ్లీ నన్ను ప్రారంభించడానికి ‘హే క్లారా’ అని చెప్పండి.",
        "hi": "मैं विराम ले रही हूँ, मुझे जगाने के लिए 'Hey Clara' कहें।",
    },
    "sleeping_ignore": {
        "en": "Clara is sleeping. Ignoring input.",
        "ta": "க்ளாரா தூங்கிக்கொண்டிருக்கிறார். உள்ளீட்டை புறக்கணிக்கிறேன்.",
        "te": "క్లారా నిద్రలో ఉంది. ఇన్‌పుట్‌ను పట్టించుకోవడం లేదు.",
        "hi": "क्लारा सो रही है। इनपुट को अनदेखा किया जा रहा है।",
    },
    "already_awake": {
        "en": "Clara is already active.",
        "ta": "க்ளாரா ஏற்கனவே செயல்பாட்டில் உள்ளார்.",
        "te": "క్లారా ఇప్పటికే యాక్టివ్‌గా ఉంది.",
        "hi": "क्लारा पहले से सक्रिय है।",
    },
    "classification_retry": {
        "en": "I didn't catch that. Are you an Employee or a Visitor?",
        "ta": "எனக்கு புரியவில்லை. நீங்கள் ஊழியரா அல்லது பார்வையாளரா?",
        "te": "నాకు అర్ధం కాలేదు. మీరు ఎంప్లాయీ లేదా విసిటర్ ?",
        "hi": "मुझे समझ नहीं आया। क्या आप कर्मचारी हैं या आगंतुक?",
    },
    "auto_sleep_notice": {
        "en": "Clara has gone idle due to inactivity. Say 'Hey Clara' to wake me up.",
        "ta": "செயல்பாட்டின்மை காரணமாக க்ளாரா ஓய்வில் உள்ளார். என்னை எழுப்ப 'Hey Clara' என்று சொல்லுங்கள்.",
        "te": "క్లారా కొన్ని సేపు యాక్టివ్‌గా లేకపోవడం వలన రెస్టుకి వెళ్ళింది. నన్ను మళ్లీ ప్రారంభించడానికి 'హే క్లారా' అని చెప్పండి.",
        "hi": "गतिविधि न होने के कारण क्लारा विराम पर है। मुझे जगाने के लिए 'Hey Clara' कहें।",
    },
    "no_speech": {
        "en": "No recognizable speech detected.",
        "ta": "அறியக்கூடிய பேச்சு எதுவும் கண்டுபிடிக்கப்படவில்லை.",
        "te": "గుర్తించగల మాట ఏదీ కనబడలేదు.",
        "hi": "कोई पहचानी जाने वाली आवाज़ नहीं मिली।",
    },
    "active_heard": {
        "en": "Clara (active) heard: {text}",
        "ta": "க்ளாரா (செயலில்) கேட்டது: {text}",
        "te": "క్లారా (యాక్టివ్) విన్నది: {text}",
        "hi": "क्लारा (सक्रिय) ने सुना: {text}",
    },
}

NORMALIZATION_MAP = {
    "ta": {
        "na": "நன",
        "kudu": "கட",
        "employee": "ஊழயர",
        "visitor": "வரநதனர",
        "ரிசர்ச்": "சர்ச்",
        "ரிப்செஸ்": "சர்ச்",
        "சர்ச்": "தேடல்",
        "ரிப்சேச்": "சர்ச்",
    },
    "te": {
    "na": "నేను",
    "kudu": "ఇవ్వండి",
    "employee": "ఎంప్లాయీ",
    "visitor": "విసిటర్",
    "talk in telugu": "తెలుగులో మాట్లాడండి",
    "speak telugu": "తెలుగులో మాట్లాడండి",
    "telugu": "తెలుగు"
    },
    "hi": {
        "na": "म",
        "employee": "करमचर",
        "talk in hindi": "हिंदी",
        "speak hindi": "हिंदी",
        "hindi": "हिंदी",
    },
    "en": {
        "talk in tamil": "talk in tamil",
        "talk in telugu": "talk in telugu",
        "talk in hindi": "talk in hindi",
    },
}

WAKE_PHRASES = {
    "en": ["hey clara"],
    "ta": ["ஹே க்ளாரா", "ஹாய் க்ளாரா", "hey clara"],
    "te": ["హే క్లారా", "హాయ్ క్లారా", "hey clara"],
    "hi": ["हे क्लारा", "hey clara"],
}


SLEEP_PHRASES = {
    "en": ["go idle", "sleep now", "take a break"],
    "ta": ["ஓய்வு எடு", "தூங்கிக்கொள்", "ஓய்வெணு", "go idle"],
    "te": ["విశ్రాంతి తీసుకో", "నిద్రపో", "అలసిపోయి విశ్రాంతి తీసుకో", "go idle"],
    "hi": ["सो जाओ", "आराम करो", "विराम लो", "go idle"],
}


def detect_language_from_text(text: str | None) -> str | None:
    if not text:
        return None

    script_counts = {"ta": 0, "te": 0, "hi": 0}
    for ch in text:
        code_point = ord(ch)
        if 0x0B80 <= code_point <= 0x0BFF:
            script_counts["ta"] += 1
        elif 0x0C00 <= code_point <= 0x0C7F:
            script_counts["te"] += 1
        elif 0x0900 <= code_point <= 0x097F:
            script_counts["hi"] += 1

    for code, count in script_counts.items():
        if count >= 2:
            return code

    normalized = text.lower().strip()
    if not normalized:
        return None

    primary = normalized.split("-")[0]
    if primary in LANGUAGE_CODE_ALIASES:
        return LANGUAGE_CODE_ALIASES[primary]

    translator = str.maketrans({char: " " for char in string.punctuation})
    tokenized = normalized.translate(translator).split()
    for token in tokenized:
        if token in LANGUAGE_CODE_ALIASES:
            return LANGUAGE_CODE_ALIASES[token]

    for keyword, code in (
        ("english", "en"),
        ("tamil", "ta"),
        ("telugu", "te"),
        ("hindi", "hi"),
    ):
        if keyword in normalized:
            return code

    return None


def resolve_language_code(label: str | None) -> str:
    detected = detect_language_from_text(label)
    if detected:
        return detected
    return DEFAULT_LANGUAGE


def get_message(key: str, lang: str, **kwargs) -> str:
    lang = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    bucket = MESSAGES.get(key, {})
    template = bucket.get(lang, bucket.get(DEFAULT_LANGUAGE, ""))
    return template.format(**kwargs)


def normalize_transcript(text: str, lang: str) -> str:
    lang = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    text = text.lower()
    replacements = NORMALIZATION_MAP.get(lang, {})
    normalized = text
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def get_wake_phrases(lang: str) -> List[str]:
    lang = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    return WAKE_PHRASES.get(lang, WAKE_PHRASES[DEFAULT_LANGUAGE])


def get_sleep_phrases(lang: str) -> List[str]:
    lang = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    return SLEEP_PHRASES.get(lang, SLEEP_PHRASES[DEFAULT_LANGUAGE])


def any_phrase_in_text(text: str, phrases: Iterable[str]) -> bool:
    text = text.lower()
    for phrase in phrases:
        if phrase and phrase.lower() in text:
            return True
    return False


__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "resolve_language_code",
    "get_message",
    "normalize_transcript",
    "get_wake_phrases",
    "get_sleep_phrases",
    "any_phrase_in_text",
]
