import json
import uuid
import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .models import ChatMessage


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

    recent_messages = ChatMessage.objects.filter(session_id=session_id).order_by('created_at')[:20]
    messages = [{
        "role": "system",
        "content": (
            "You are VetCare's AI Pet Health Assistant. Your role is to provide GENERAL INFORMATION ONLY about pet health and care. "
            "You are NOT a licensed veterinarian and CANNOT diagnose, prescribe, or treat medical conditions. "
            "You can respond in Bangla, English, or both (Banglish/mixed) depending on the user's question. "
            "Detect the user's language automatically and reply in the same style. "
            "\n\n"
            "STRICT GUIDELINES - MUST FOLLOW:\n"
            "- NEVER prescribe specific medicines, dosages, or treatments. Do NOT recommend specific drugs by name for treating a condition.\n"
            "- You may mention general wellness items (e.g., 'clean water', 'balanced diet', 'vitamin supplements from pet stores') but NOT specific medications for a disease.\n"
            "- For ANY symptoms described, respond with: general information about what it MIGHT indicate, general care tips (rest, hydration, warmth, clean environment), and a STRONG recommendation to see a licensed vet.\n"
            "- Do NOT attempt to diagnose. Always say: 'I cannot diagnose this. Please consult a licensed veterinarian.'\n"
            "- For emergencies (bleeding, seizures, breathing difficulty, poisoning, collapse, broken bones): respond ONLY with urgent advice to visit the nearest vet clinic or emergency animal hospital immediately.\n"
            "- Keep responses within 100 words MAX. Be concise and focused.\n"
            "- Use bullet points or short numbered steps when helpful.\n"
            "- Always end every response with: 'I am an AI assistant, not a vet. Please consult a licensed veterinarian for proper diagnosis and treatment.'\n"
            "- Do not repeat the question. Do not add unnecessary preamble.\n"
            "- Do not provide instructions that could be harmful if misused.\n"
            "- Note: Text-only assistant, cannot analyze images."
        )
    }]
    for msg in recent_messages:
        role = "user" if msg.sender == "USER" else "assistant"
        content = msg.message
        messages.append({"role": role, "content": content})

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
    except requests.RequestException:
        bot_reply = "I'm having trouble connecting right now. Please try again later."
    except (KeyError, IndexError, TypeError):
        bot_reply = "Sorry, I received an unexpected response. Please try again."

    ChatMessage.objects.create(session_id=session_id, sender='BOT', message=bot_reply)
    return JsonResponse({'reply': bot_reply})
