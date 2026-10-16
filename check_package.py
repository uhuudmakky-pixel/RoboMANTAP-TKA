from pathlib import Path
import ast, json, zipfile
ROOT = Path(__file__).resolve().parent
for path in [ROOT/'tka_main.py', ROOT/'tka_engine.py', ROOT/'ai_engine.py', ROOT/'api'/'index.py']:
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
engine=(ROOT/'tka_engine.py').read_text(encoding='utf-8')
ai=(ROOT/'ai_engine.py').read_text(encoding='utf-8')
main=(ROOT/'tka_main.py').read_text(encoding='utf-8')
assert 'TKA_TOTAL_QUESTIONS = 15' in engine
assert 'TKA_STUDIO_ALLOWED_COUNTS = (15, 20, 25)' in engine
assert 'OPTION_LABELS_MTS = ("A", "B", "C", "D")' in ai
assert 'OPTION_LABELS_MA = ("A", "B", "C", "D", "E")' in ai
assert 'templates-tka' in main
login=(ROOT/'templates-tka'/'student_login.html').read_text(encoding='utf-8')
assert 'tepat 15 soal' in login and '15 soal</b> • Durasi 75 menit' in login
assert 'TKA_STUDIO_ALLOWED_COUNTS = (15, 20, 25)' in engine
assert (ROOT/'templates-tka'/'student_login.html').is_file()
assert (ROOT/'templates-tka'/'student_exam.html').is_file()
assert (ROOT/'templates-tka'/'student_result.html').is_file()
conf=json.loads((ROOT/'vercel.json').read_text(encoding='utf-8'))
assert any(b.get('src')=='api/index.py' for b in conf.get('builds',[]))
print('PASS: syntax, constants, templates, Vercel entrypoint')
