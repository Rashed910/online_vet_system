import os
import django
import sys

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vetcure.settings')
django.setup()

from chatbot.views import find_knowledge_match, detect_language

tests = [
    'My cat has diarrhea',
    'আমার বিড়াল দস্ত করছে',
    'not eating food',
    'খাবার খায় না',
    'ear infection',
    'কান বেঁচে',
    'skin allergy',
    'চামড়ায় খুঁজি',
    'my dog is vomiting',
    'কুকুর বমি করছে',
]

for t in tests:
    lang = detect_language(t)
    match = find_knowledge_match(t)
    result = f'Lang: {lang}, Match: {"YES" if match else "NO"} - {t[:30]}'
    print(result)