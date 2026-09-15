import json
import uuid
import re
import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .models import ChatMessage


PET_HEALTH_KNOWLEDGE = {
    'en': {
        'ear_infection': {
            'keywords': ['ear', 'itch', 'scratch ear', 'head shake', 'discharge', 'smell', 'infection', 'কান', 'চুলকাচ্ছে', 'ইয়ার', 'হাতে কানি', 'গন্ধ', 'পুঁত', 'কান বেঁচে', 'কানের ইনফেকশন'],
            'reply': (
                "Ear problems in pets - possible causes:\n"
                "• Ear mites (common in cats/puppies)\n"
                "• Bacterial or yeast infection\n"
                "• Allergies (food/environmental)\n"
                "• Foreign object or injury\n\n"
                "Immediate care:\n"
                "• Do NOT put human medicine/drops in ears\n"
                "• Keep ear dry - no swimming/baths\n"
                "• Gently wipe outer ear with damp cloth\n"
                "• Prevent scratching with e-collar if needed\n\n"
                "See vet within 24-48 hours for:\n"
                "• Otoscopic exam & cytology\n"
                "• Proper medication (antibiotic/antifungal drops)\n"
                "• Ear cleaning under sedation if severe\n\n"
                "I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment."
            )
        },
        'vomiting': {
            'keywords': ['vomit', 'throwing up', 'vomiting', 'regurgitate', 'বমি', 'বমি করছে', 'থ্রো আপ', 'উল্টি', 'বমি করল', 'কামলা দিয়ে বমি', 'খাবার বমি করল'],
            'reply': (
                "Vomiting in pets - common causes:\n"
                "• Dietary indiscretion (ate something bad)\n"
                "• Food intolerance/allergy\n"
                "• Parasites (worms)\n"
                "• Infections (viral/bacterial)\n"
                "• Organ disease (kidney/liver/pancreas)\n\n"
                "Home care (if mild, single episode):\n"
                "• Withhold food 12-24 hours (water OK)\n"
                "• Then offer bland diet: boiled chicken + rice\n"
                "• Small, frequent meals\n\n"
                "EMERGENCY - go to vet NOW if:\n"
                "• Vomiting >24 hours or >3 times/day\n"
                "• Blood in vomit (coffee grounds)\n"
                "• Also has diarrhea/lethargy/pain\n"
                "• Puppy/kitten or senior pet\n"
                "• Known toxin ingestion\n\n"
                "I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment."
            )
        },
        'diarrhea': {
            'keywords': ['diarrhea', 'diarrhoea', 'loose stool', 'loose motion', 'দস্ত', 'লুকামনা', 'লুজ মোশন', 'পাতলা মল', 'পেট খারাপ', 'বারবার দস্ত', 'রক্তে দস্ত'],
            'reply': (
                "Diarrhea in pets - common causes:\n"
                "• Sudden diet change\n"
                "• Stress/anxiety\n"
                "• Parasites (giardia, coccidia, worms)\n"
                "• Bacterial/viral infection\n"
                "• Food intolerance\n\n"
                "Home care:\n"
                "• Ensure hydration - offer water frequently\n"
                "• Bland diet: boiled chicken + white rice (2:1)\n"
                "• Probiotic supplement (pet-specific)\n"
                "• Monitor for blood/mucus\n\n"
                "See vet if:\n"
                "• Persists >24-48 hours\n"
                "• Blood or black tarry stool\n"
                "• Vomiting + diarrhea combined\n"
                "• Lethargy, fever, or dehydration\n"
                "• Very young/old/small breed\n\n"
                "I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment."
            )
        },
'not_eating': {
            'keywords': ['not eating', 'anorexia', 'refuses food', "won't eat", 'loss of appetite', 'khaya nai', 'খায় না', 'খাবার খায় না', 'খেলে না', 'খাবার খেলে না', 'খাদ্য না নেয়', 'খাদ্য বর্জন', 'অনোরেক্সিয়া', 'অনুখাদ্য', 'ভুক কম', 'নাকাচ্ছে না'],
            'reply': (
                "Pet not eating - possible causes:\n"
                "• Dental pain (broken tooth, gingivitis)\n"
                "• Nausea/GI upset\n"
                "• Stress/environmental change\n"
                "• Recent vaccination\n"
                "• Serious illness (kidney, liver, cancer)\n\n"
                "Try at home:\n"
                "• Warm food slightly (enhances smell)\n"
                "• Offer tasty topper: broth, wet food, egg\n"
                "• Hand feed small amounts\n"
                "• Check mouth for visible issues\n\n"
                "See vet if:\n"
                "• No food >24 hours (cats: >12 hours critical)\n"
                "• Also vomiting/diarrhea/lethargy\n"
                "• Weight loss visible\n"
                "• Drooling, pawing at mouth\n\n"
                "I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment."
            )
        },
        'lethargy': {
            'keywords': ['lethargic', 'lethargy', 'weak', 'tired', 'low energy', 'not moving', 'দুর্বল', 'ক্লান্তি', 'জড়তা', 'শক্তি নেই', 'উঠতে পারছে না', 'বসেই আছে', 'চলে না', 'উদাস'],
            'reply': (
                "Lethargy/weakness in pets - warning signs:\n"
                "• Could indicate: infection, pain, anemia, heart disease, poisoning\n"
                "• Check: gum color (should be pink), breathing rate, temperature\n\n"
                "Immediate steps:\n"
                "• Keep warm, quiet, comfortable\n"
                "• Offer water (syringe if needed)\n"
                "• Do NOT force exercise\n\n"
                "EMERGENCY - vet NOW if:\n"
                "• Collapse/unresponsive\n"
                "• Pale/white/blue gums\n"
                "• Difficulty breathing\n"
                "• Bloated abdomen\n"
                "• Known toxin exposure\n\n"
                "I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment."
            )
        },
        'skin_allergies': {
            'keywords': ['itchy', 'scratching', 'allergies', 'rash', 'hot spot', 'licking paws', 'খুঁজি', 'চুলকানি', 'অ্যালার্জি', 'দাগ', 'পা হাত চাটছে', 'শরীরে দানা', 'চামড়া লাল', 'র‍্যাশ'],
            'reply': (
                "Skin allergies/itching in pets:\n"
                "• Common causes: fleas, food allergy, environmental (pollen/dust)\n"
                "• Flea allergy = most common (even 1 flea!)\n\n"
                "Home care:\n"
                "• Year-round flea prevention (vet-approved)\n"
                "• Oatmeal bath or medicated shampoo\n"
                "• E-collar to prevent self-trauma\n"
                "• Wipe paws after outdoors\n\n"
                "Vet treatments:\n"
                "• Apoquel/Cytopoint (prescription only)\n"
                "• Antihistamines (vet dose only)\n"
                "• Elimination diet trial (8-12 weeks)\n"
                "• Allergy testing/immunotherapy\n\n"
                "I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment."
            )
        },
        'antibiotic_human': {
            'keywords': ['human antibiotic', 'antibiotic', 'amoxicillin', 'human medicine', 'human pill', 'মানুষের অ্যান্টিবায়োটিক', 'অ্যান্টিবায়োটিক', 'মানুষের ওষধ', 'গোটি', 'ট্যাবলেট', 'মানুষের মেডিসিন', 'এমক্সিসিলিন', 'কোনো ওষধ দিব কি'],
            'reply': (
                "NEVER give human antibiotics to pets:\n"
                "• Different metabolism - toxic doses possible\n"
                "• Wrong antibiotic for pet's bacteria\n"
                "• Can cause: vomiting, diarrhea, kidney/liver damage, death\n"
                "• Antibiotic resistance risk\n\n"
                "Only a vet can:\n"
                "• Culture infection to identify bacteria\n"
                "• Prescribe correct pet antibiotic & dose\n"
                "• Monitor for side effects\n\n"
                "I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment."
            )
        },
        'emergency': {
            'keywords': ['emergency', 'bleeding', 'seizure', 'breathing', 'poison', 'toxin', 'collapse', 'choking', 'hit by car', 'জরুরি', 'এমারজেন্সি', 'রক্ত', 'শিকলান', 'শ্বাসকষ্ট', 'বিষ', 'পড়ে যাচ্ছে', 'দুর্ঘটনা', 'গ্লানি', 'অচেতন', 'রক্তপাত', 'হার্ট অ্যাটাক', 'স্ট্রোক'],
            'reply': (
                "PET EMERGENCY - GO TO VET IMMEDIATELY:\n\n"
                "• Bleeding: apply pressure, don't remove object\n"
                "• Seizure: clear area, time it, don't touch mouth\n"
                "• Breathing trouble: keep calm, upright position\n"
                "• Poison: call ASPCA 888-426-4435, bring label\n"
                "• Collapse: check breathing/heartbeat, CPR if needed\n"
                "• Choking: try to remove if visible, Heimlich if not\n\n"
                "Transport: keep warm, minimize movement, call ahead.\n\n"
                "I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment."
            )
        },
        'bird_parasites': {
            'keywords': ['bird', 'parrot', 'parakeet', 'budgie', 'canary', 'finch', 'feather', 'mite', 'louse', 'lice', 'flea', 'parasite', 'anthelmintic', 'dewormer', 'syrup', 'ivermectin', 'fenbendazole', 'পাখি', 'পাখির চুলকানি', 'মাইট', 'জুঁই', 'পোকা', 'প্যারাসাইট', 'প্যারাসিটামল', 'ডিউয়ার্মার', 'সিরাপ', 'আইভারমেক্টিন', 'ফেনবেন্ডাজোল'],
            'reply': (
                "Bird external parasites (mites, lice, fleas on feathers):\n\n"
                "• Common causes:\n"
                "  • Feather mites / red mites (nocturnal)\n"
                "  • Scaly face/leg mites (knemidokoptes)\n"
                "  • Lice (mallophaga - chewing lice)\n"
                "  • Poor cage hygiene / wild bird contact\n"
                "  • Stress / immunosuppression\n\n"
                "• Immediate care:\n"
                "  • Do NOT give human or dog/cat dewormers\n"
                "  • Do NOT use anthelmintic syrups without avian vet\n"
                "  • Birds have unique metabolism - toxic doses common\n"
                "  • Clean cage thoroughly: wash perches, dishes, toys\n"
                "  • Isolate affected bird from others\n"
                "  • Provide fresh water, reduce stress\n\n"
                "• Avian vet will:\n"
                "  • Identify parasite via microscopy\n"
                "  • Prescribe bird-safe treatment (ivermectin, moxidectin, selamectin - vet dose only)\n"
                "  • Treat environment to prevent reinfestation\n\n"
                "I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment."
            )
        },
    },
}


def detect_language(message):
    bangla_count = len(re.findall(r'[\u0980-\u09FF]', message))
    english_count = len(re.findall(r'[a-zA-Z]', message))
    if bangla_count > english_count:
        return 'bn'
    return 'en'


def find_knowledge_match(message, lang='en'):
    msg_lower = message.lower()
    knowledge = PET_HEALTH_KNOWLEDGE['en']
    
    best_match = None
    best_score = 0
    
    for category, data in knowledge.items():
        for kw in data['keywords']:
            kw_lower = kw.lower()
            # Check if keyword contains non-ASCII characters (Bangla)
            has_bangla = any(ord(c) > 127 for c in kw_lower)
            
            if has_bangla:
                # For Bangla keywords, use simple substring matching with boundary checks
                # Match at word boundaries (space, punctuation, start/end of string)
                pattern = r'(^|[\s\W])' + re.escape(kw_lower) + r'($|[\s\W])'
                if re.search(pattern, msg_lower):
                    score = len(kw_lower)
                    if score > best_score:
                        best_score = score
                        best_match = data['reply']
            else:
                # For English keywords, use word boundaries
                pattern = r'\b' + re.escape(kw_lower) + r'\b'
                if re.search(pattern, msg_lower):
                    score = len(kw_lower)
                    if score > best_score:
                        best_score = score
                        best_match = data['reply']
    
    return best_match


def is_unsafe_response(reply):
    unsafe_keywords = ['prescribe', 'dosage', 'mg', 'tablet', 'pill', 'inject', 'prescription', 'medicine', 'diagnose', 'diagnosis']
    lower = reply.lower()
    if 'not a vet' in lower or 'consult a licensed' in lower or 'emergency' in lower or 'ডাক্তার' in lower or 'জরুরি' in lower:
        return False
    return any(kw in lower for kw in unsafe_keywords)


@login_required
def chatbot_view(request):
    session_id = request.session.session_key or str(uuid.uuid4())
    if not request.session.session_key:
        request.session['chatbot_session_id'] = session_id
    
    # Load previous messages for this session
    previous_messages = ChatMessage.objects.filter(session_id=session_id).order_by('created_at')[:50]
    
    return render(request, 'chatbot.html', {
        'session_id': session_id,
        'previous_messages': previous_messages,
    })


@login_required
@require_POST
def chat_api(request):
    session_id = request.session.get('chatbot_session_id') or request.session.session_key or str(uuid.uuid4())
    if not request.session.get('chatbot_session_id'):
        request.session['chatbot_session_id'] = session_id

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        if not user_message:
            return JsonResponse({'error': 'Empty message'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    ChatMessage.objects.create(session_id=session_id, sender='USER', message=user_message)

    lang = detect_language(user_message)
    knowledge_reply = find_knowledge_match(user_message, lang)

    recent_messages = ChatMessage.objects.filter(session_id=session_id).order_by('created_at')[:20]
    messages = [{
        "role": "system",
        "content": (
            "You are VetCare's AI Pet Health Assistant. Provide GENERAL pet health info only. "
            "You are NOT a licensed veterinarian and CANNOT diagnose, prescribe, or treat. "
            "ALWAYS respond in ENGLISH only, regardless of user's language.\n\n"
            "RESPONSE FORMAT - MUST USE:\n"
            "• Bullet points (•) for lists\n"
            "• Clear sections with headers\n"
            "• Numbered steps for procedures\n"
            "• Bold for emphasis\n\n"
            "RULES:\n"
            "1. NEVER diagnose, prescribe medications, or give specific dosages.\n"
            "2. For symptoms: list possible causes, suggest basic care, ALWAYS recommend seeing a vet.\n"
            "3. For emergencies: say 'Take to emergency vet IMMEDIATELY' and give ONLY basic first aid steps.\n"
            "4. NEVER mention specific drug names as treatment.\n"
            "5. End EVERY reply with: 'I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment.'\n"
            "6. Keep responses under 120 words.\n"
            "7. Be clear, structured, and consistent."
        )
    }]
    for msg in recent_messages:
        role = "user" if msg.sender == "USER" else "assistant"
        content = msg.message
        messages.append({"role": role, "content": content})

    if knowledge_reply:
        bot_reply = knowledge_reply
    else:
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://vetcare.example.com",
                    "X-OpenRouter-Title": "VetCare Pet Health Assistant",
                },
                data=json.dumps({
                    "model": "openrouter/free",
                    "messages": messages,
                    "max_tokens": 500,
                }),
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            bot_reply = result.get('choices', [{}])[0].get('message', {}).get('content', 'Sorry, I could not generate a response.')

            if is_unsafe_response(bot_reply):
                bot_reply = "I cannot diagnose this. Please consult a licensed veterinarian. I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment."

            if not bot_reply.strip():
                bot_reply = "I'm sorry, I didn't understand. Please describe your pet's symptoms."

        except requests.RequestException:
            bot_reply = "I'm having trouble connecting right now. Please try again later."
        except (KeyError, IndexError, TypeError):
            bot_reply = "Sorry, I received an unexpected response. Please try again."

    ChatMessage.objects.create(session_id=session_id, sender='BOT', message=bot_reply)
    return JsonResponse({'reply': bot_reply})