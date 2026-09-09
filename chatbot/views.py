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


BANGLA_KEYWORDS = ['বিড়াল', 'কুকুর', 'বাংলা', 'বাংলায়', 'করছে', 'দুর্বল', 'বমি', 'খায়', 'খাওয়ান', 'পেট', 'দেহ', 'রক্ত', 'ফাটল', 'চুলকানি', 'শিকলান', 'হাঁচি', 'জ্বর', 'তাকত', 'ক্লান্তি']


COMMON_REPLIES = {
    'en': {
        'vomit|vomiting|vomited|throwing up': "Your pet may have eaten something bad or have an upset stomach. Offer small sips of water, keep them calm, and watch for other symptoms. If vomiting continues >12 hours or has blood, contact a vet immediately.",
        'diarrhea|diarrhoea|loose_motion': "Diarrhea could be from diet change, infection, or stress. Keep your pet hydrated with small water amounts. If it persists >24 hrs, has blood, or pet seems weak, see a vet.",
        'not_eating|anorexia|appetite': "Not eating can indicate illness, stress, or pain. Try warming their food. If no eating for >24 hours, contact a vet.",
        'fever|hot': "Fever (>103°F/39.4°C) signals infection. Keep pet cool, offer water. Do NOT give human fever medicine. A vet must check this.",
        'lethargy|depressed|weak|lethargic': "Your pet seems unusually tired or inactive. Check for fever, dehydration, or injury. Keep them comfortable and quiet. If severe or sudden, this could be serious - see a vet promptly.",
        'coughing|cough': "Coughing can be from allergies, kennel cough, or trachea problems. Keep your pet calm, avoid irritants. If persists >24 hrs with breathing trouble, see a vet.",
        'bleeding|blood|hemorrhage': "EMERGENCY: Uncontrolled bleeding requires immediate vet care. Apply gentle pressure with a clean cloth. Go to nearest emergency vet NOW.",
        'seizure|convulsion': "EMERGENCY: Keep pet away from hard surfaces. Do NOT put hands in mouth. Time the episode. Take to emergency vet IMMEDIATELY after it stops.",
        'breathing|wheezing': "EMERGENCY: Difficulty breathing is life-threatening. Keep pet calm in a ventilated area. Take to emergency vet IMMEDIATELY.",
        'poison|toxin|toxic': "EMERGENCY: Call emergency vet or pet poison control NOW. Have the substance label ready. Do NOT induce vomiting unless told by a vet.",
        'fracture|broken|limp|lameness': "Possible fracture or injury needs immediate vet attention. Keep pet still, do NOT let them walk on injured limb. Apply splint if trained. See vet now.",
        'itchy|scratching|allergies|scratch': "Itchy skin is often from allergies or fleas. Check for fleas, bathe with gentle pet shampoo. If excessive or has sores, see a vet.",
        'diabetes|insulin': "Diabetes requires insulin injections and monitoring. Symptoms: excessive thirst, urination, weight loss. Needs veterinary diagnosis and management.",
        'vaccination|vaccine': "Vaccinations prevent diseases. Core vaccines for dogs include rabies, distemper, parvovirus. Schedule with your vet.",
        'heat_stroke|overheating': "EMERGENCY: Move to shade/AC, apply cool water, offer small sips of water. Take to vet IMMEDIATELY - this is life-threatening.",
        'antibiotic|antibiotics|human medicine|medicine|tablet|pill|drug': "NEVER give human antibiotics, pills, or medicine to pets without vet approval. This can be toxic. Take your pet to a vet for proper treatment.",
        'ear|চুলকাচ্ছে|ইয়ার': "Ear problems can be from infection, mites, or injury. Do NOT put human medicine in ears. Keep the ear dry and clean. See a vet for proper diagnosis and treatment.",
    },
    'bn': {
        'vomit|বমি|বমি করছে|থ্রো আপ': "আপনার পোকামাকড় খেয়েছে খারাপ কিছু বা পেট খারাপ করছে। ছোট ছোট ঘূর্ণি দিন, শান্ত রাখুন। যদি বমি থেকে ১২ ঘণ্টার বেশি হয় বা রক্ত আসে ডাক্তারের দিকে যান।",
        'diarrhea|দস্ত|লুকামনা': "দস্ত হতে পারে খাদ্য পরিবর্তন, সংক্রমণ বা স্ট্রেস থেকে। পোকামাকড়কে ছোট ছোট পানি খান। যদি ২৪ ঘণ্টার বেশি থাকে বা রক্ত আসে দুর্বল মনে হয় ডাক্তারের দিকে যান।",
        'not_eating|not eating|khaya nai|খায় না|খায় না': "খাওয়া বন্ধ করা বামাকাল অসুস্থতা, স্ট্রেস বা ব্যথা ইঙ্গিত করতে পারে। তাকে গরম করে খাবার দেওয়ার চেষ্টা করুন। যদি ২৪ ঘণ্টার বেশি না খায় তাকে ডাক্তারের দিকে নিন।",
        'fever|জ্বর|গরম': "জ্বর (>৩৯.৪°সে) সংক্রমণ বা অসুস্থতার সংকেত। পোকামাকড়কে শীতল রাখুন, পানি দিন। মানব জ্বর ওষধ দেবেন না। এটি ডাক্তারের যাচাই প্রয়োজন।",
        'lethargy|depressed|weak|দুর্বল|ক্লান্তি|তাকত': "আপনার পোকামাকড় অজানাতা থাকাকালীন ক্লান্ত বা জড়তা করছে। জ্বর, ডিহাইড্রেশন বা আঘাত চেক করুন। তাকে আরামদায়ক ও নিশ্চুপ রাখুন। যদি গুরুতর বা হঠাৎ হয় তাকে ডাক্তারের দিকে যান।",
        'coughing|কাশি|কার': "কাশি হতে পারে অ্যালার্জি, কেনেল কাশি বা ত্রাকিয়া সমস্যা থেকে। পোকামাকড়কে শান্ত রাখুন, উত্তেজনাকর জিনিস থেকে বাদ দিন। যদি ২৪ ঘণ্টার বেশি হয় শ্বাসের সমস্যার সাথে ডাক্তারের দিকে যান।",
        'bleeding|রক্ত|hemorrhage': "এমারজেন্সি: অনিয়ন্ত্রিত রক্তপাত এখনই ডাক্তারের দিকে নিন। পরিষ্কার চাদর দিয়ে মৃদু চাপ প্রয়োগ করুন। জানালো জরুরি ডাক্তারে যান এখনই।",
        'seizure|শিকলান|শিকলান': "এমারজেন্সি: যখন শিকলান শুরু হয় শক্ত উপরের পৃষ্ঠের দিকে না রাখুন। মুখের ভেতরে হাত না রাখুন। সময় নিন। শিকলান থেকে পরে জরুরি ডাক্তারে যান।",
        'breathing|শ্বাসের সমস্যা|শ্বাসকষ্ট': "এমারজেন্সি: শ্বাস নেওয়া দুর্বলতা পূর্ণ। পোকামাকড়কে শান্ত ও বায়ুমণ্ডলীয় ক্ষেত্রে রাখুন। জরুরি ডাক্তারে যান এখনই।",
        'poison|toxin|ভুষ্যা|বিষ': "এমারজেন্সি: যদি পোকামাকড় কিছু ভুষ্যা খেয়েছে তাকে এখনই জরুরি ডাক্তার বা ভুষ্যা নিয়ন্ত্রণ কেন্দ্রে যান। আপত্তির উপাদান লেবেল রাখুন। বমি তোলার জন্য বলতে চাবেন না যদি ডাক্তার না বলেন।",
        'fracture|ভাঁজ|ফাটল|চোট': "ভাঁজ বা আঘাত এখনই ডাক্তারের যাত্তা সংকেত। পোকামাকড়কে থামিয়ে রাখুন, আঘাতজনিত পায় ব্যবহার করে না। যদি প্রশিক্ষিত হয় স্প্লিন্ট প্রয়োগ করুন। ডাক্তারের দিকে যান।",
        'itchy|খুঁজি|allergies|চুলকানি|দাগ': "খুঁজি পোকামাকড়ের অ্যালার্জি বা পোকা থেকে হতে পারে। পোকা চেক করুন, মৃদু পোকামাকড় শ্যাম্পু দিয়ে নাবালায়। যদি অতিরিক্ত হয় বা সাদ্রায় হয় ডাক্তারের দিকে যান।",
        'diabetes|ডায়াবেটিস|ইনসুলিন': "ডায়াবেটিস ইনসুলিন ইঞ্জেকশন এবং নজরদারি প্রয়োজন। লক্ষণ: অতিরিক্ত তৃষ্ণা, মূত্য, ওজন ক্ষয়। ভ্যাকটরি নির্ণয় ও পরিচর্যা প্রয়োজন।",
        'vaccination|টিকা|টিকা': "টিকা রোগ প্রতিরোধ পায়। কুকুরের জন্য মূল টিকাগুলোতে রেড শিক, ডিস্টেনফেক্ট এবং প্যারভোভাসিস। আপনার ডাক্তারের সাথে অ্যাপয়েন্টমেন্ট নিন।",
        'heat_stroke|অতিতাপ|ওভারহিটিং': "এমারজেন্সি: ছাড়া/এসিতে নিন, ঠান্ডা পানি লাগান, ছোট ছোট ঘূর্ণি দিন। এটি জীবন বিরণ্টিত - ডাক্তারের দিকে যান এখনই।",
        'antibiotic|antibiotics|অ্যান্টিবায়োটিক|medicine|drug|tablet|pill': "পোকামাকড়ের জন্য মানুষের অ্যান্টিবায়োটিক, গুলো বা ওষধ দেওয়া ঠিক বাদ দিন - এটি ক্ষতিকর হতে পারে। সঠিক চিকিৎসার জন্য একজন ভেটারিনারী ডাক্তারের দিকে যান।",
        'ear|কান|চুলকাচ্ছে|ইয়ার': "কানের সমস্যা অস্যাঙ্গের সংক্রমণ, পোকা বা আঘাত থেকে হতে পারে। মানুষের ওষধ কানে দেবেন না। কানটি শুকতে রাখুন ও পরিষ্কার রাখুন। সঠিক নির্ণয় ও চিকিৎসার জন্য ডাক্তারের দিকে যান।",
    },
}


def detect_language(message):
    bangla_count = len(re.findall(r'[\u0980-\u09FF]', message))
    english_count = len(re.findall(r'[a-zA-Z]', message))
    if bangla_count > english_count:
        return 'bn'
    return 'en'


def get_common_reply(message, lang='en'):
    patterns = COMMON_REPLIES[lang]
    msg_lower = message.lower()
    for pattern, reply in patterns.items():
        if re.search(pattern, msg_lower):
            return reply
    return None


def is_unsafe_response(reply):
    unsafe_keywords = ['prescribe', 'dosage', 'mg', 'tablet', 'pill', 'inject', 'prescription', 'medicine', 'diagnose', 'diagnosis']
    lower = reply.lower()
    if 'not a vet' in lower or 'consult a licensed' in lower or 'emergency' in lower or 'ডাক্তার' in lower or 'emarjan' in lower:
        return False
    return any(kw in lower for kw in unsafe_keywords)


DISCLAIMER_BN = " আমি একজন এআই সহায়ক, ডাক্তার নই। আপনার পোকামাকড়ের সঠিক নির্ণয় ও চিকিৎসার জন্য অবশ্যই একজন অনুমোদিত ভেটের কাছে যান।"
DISCLAIMER_EN = " I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment."


@login_required
def chatbot_view(request):
    session_id = request.session.session_key or str(uuid.uuid4())
    if not request.session.session_key:
        request.session['chatbot_session_id'] = session_id
    return render(request, 'chatbot.html', {'session_id': session_id})


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
    common_reply = get_common_reply(user_message, lang)

    recent_messages = ChatMessage.objects.filter(session_id=session_id).order_by('created_at')[:20]
    messages = [{
        "role": "system",
        "content": (
            "You are VetCare's AI Pet Health Assistant. Provide GENERAL pet health info only. "
            "You are NOT a licensed veterinarian and CANNOT diagnose, prescribe, or treat. "
            "Respond in the same language the user writes (Bangla, English, or Banglish).\n\n"
            "RULES:\n"
            "1. NEVER diagnose, prescribe medications, or give specific dosages.\n"
            "2. For symptoms: mention what it MIGHT mean, suggest basic care (rest, water, vet visit), ALWAYS recommend seeing a vet.\n"
            "3. For emergencies (bleeding, seizures, breathing trouble, poisoning, collapse, fractures): say 'Take to emergency vet IMMEDIATELY' and give ONLY basic first aid steps.\n"
            "4. NEVER mention specific drug names as treatment.\n"
            "5. End EVERY reply with a disclaimer: for Bangla use 'আমি একজন এআই সহায়ক, ডাক্তার নই।', for English use 'I am an AI assistant, not a vet.'\n"
            "6. Keep responses under 80 words.\n"
            "7. Be clear, direct, and consistent."
        )
    }]
    for msg in recent_messages:
        role = "user" if msg.sender == "USER" else "assistant"
        content = msg.message
        messages.append({"role": role, "content": content})

    if common_reply:
        disclaimer = DISCLAIMER_BN if lang == 'bn' else DISCLAIMER_EN
        bot_reply = common_reply + disclaimer
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
                    "max_tokens": 400,
                }),
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            bot_reply = result.get('choices', [{}])[0].get('message', {}).get('content', 'Sorry, I could not generate a response.')

            if is_unsafe_response(bot_reply):
                disclaimer = DISCLAIMER_BN if lang == 'bn' else DISCLAIMER_EN
                bot_reply = "আমি এটি নির্ণয় করতে পারি না। অনুগ্রহ করে একজন অনুমোদিত ভেটের কাছে যান।" + disclaimer if lang == 'bn' else "I cannot diagnose this. Please consult a licensed veterinarian." + disclaimer

            if not bot_reply.strip():
                bot_reply = "I'm sorry, I didn't understand. Please describe your pet's symptoms." if lang == 'en' else "আমি দুঃখিত, আমি বুঝতে পারিনি। আপনার পোকামাকড়ের লক্ষণ লিখুন।"

        except requests.RequestException:
            if common_reply:
                disclaimer = DISCLAIMER_BN if lang == 'bn' else DISCLAIMER_EN
                bot_reply = common_reply + disclaimer
            else:
                bot_reply = "আমি এখনই সংযোগ করতে ব্যর্থ। অনুগ্রহ করে আবার চেষ্টা করুন।" if lang == 'bn' else "I'm having trouble connecting right now. Please try again later."
        except (KeyError, IndexError, TypeError):
            if common_reply:
                disclaimer = DISCLAIMER_BN if lang == 'bn' else DISCLAIMER_EN
                bot_reply = common_reply + disclaimer
            else:
                bot_reply = "দুঃখিত, অপ্রত্যাশিত প্রতিক্রিয়া পায়েছি। অনুগ্রহ করে আবার চেষ্টা করুন।" if lang == 'bn' else "Sorry, I received an unexpected response. Please try again."

    ChatMessage.objects.create(session_id=session_id, sender='BOT', message=bot_reply)
    return JsonResponse({'reply': bot_reply})
