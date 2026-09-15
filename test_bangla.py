import re
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

msg = 'আমার বিড়াল বমি করছে'
kw = 'বমি করছে'
pattern = r'\b' + re.escape(kw) + r'\b'
with open('test_output.txt', 'w', encoding='utf-8') as f:
    f.write(f'Pattern: {pattern}\n')
    f.write(f'Match with boundaries: {re.search(pattern, msg.lower())}\n')
    f.write(f'Match without boundaries: {re.search(re.escape(kw), msg.lower())}\n')

    # Test with English
    msg2 = 'my cat is vomiting'
    kw2 = 'vomiting'
    pattern2 = r'\b' + re.escape(kw2) + r'\b'
    f.write(f'English pattern: {pattern2}\n')
    f.write(f'English match: {re.search(pattern2, msg2.lower())}\n')
    
    # Test Bangla word boundary
    f.write(f'Bangla word char test: {re.search(r"\\w", "ব")}\n')