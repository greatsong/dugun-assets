# 소리 만드는 코드 (사본)

`audio/`의 음악 · 효과음을 만든 코드입니다. 모두 파이썬 + numpy로 직접 합성했고, 외부 음원 · 샘플은 쓰지 않았습니다.
씨앗값이 고정이라 같은 코드로 돌리면 같은 소리가 나옵니다.

| 파일 | 만드는 소리 |
|---|---|
| `outro_synth.py` | 끝 화면 음악 A 항해 마림바 · B 오르골 왈츠 · C 우쿨렐레 산책 (15초) |
| `outro_synth2.py` | 끝 화면 음악 D 로파이 건반 · E 피치카토 발걸음 · F 8비트 모험 · G 햇살 기타 · H 상쾌한 신스팝 · I 관악대 행진 (15초) |
| `bgm.py` | 배경 음악 '건반'(keys) 토막 A1 · A2 · B1 · B2 (48초 + 꼬리 4초) |
| `model_kepler/music.py` | 극장판 「모델이란 무엇인가」 음악 후보 (촛불 서재 · 별 헤는 밤 · 옛 시계 공방 · 교실 음악 · 발견의 순간) |
| `model_kepler/sfx.py` | 같은 편의 효과음 12개 |
| `make_loop.py` | 배경 곡을 마디 끝에서 자르고 남는 잔향 꼬리를 곡 처음에 겹쳐 **반복용 판**으로 만든다(건반 A1 · A2 · B1 · B2) |
| `model_kepler/loops.py` | 「촛불 서재」 · 「별 헤는 밤」 · 「옛 시계 공방」의 반복용 판(같은 코드 · 같은 씨앗값으로 다시 합성, 끝맺음 마디를 빼고 잔향을 처음에 겹침) |
| `sfx_class.py` | 교실 · 예능 효과음 32가지 × 1~3번 버전(퀴즈 생각 시간 · 정답 딩동 · 띠용 · 두둥 · 박수 …) |
| `zzfx.py` | ZzFX(Frank Force, MIT 라이선스 — 파일 안에 원문 고지)를 numpy로 옮긴 것. `sfx_class.py`의 짧은 신호음 몇 개가 쓴다 |

```bash
pip install numpy
python3 tools/sound/outro_synth.py A 8.0 10.4 a.wav        # 곡, 왕관 반짝(초), 종(초), 저장할 파일
python3 tools/sound/outro_synth2.py all 8.0 10.4 ./out     # D~I 전부
python3 tools/sound/model_kepler/sfx.py                    # → tools/sound/model_kepler/out/
python3 tools/sound/model_kepler/music.py A B              # → tools/sound/model_kepler/out/
python3 tools/sound/model_kepler/loops.py                  # 반복용 판 → tools/sound/model_kepler/out/*_loop.wav
python3 tools/sound/make_loop.py keys_A1.wav 3.0 16 keys_A1_loop.wav   # 원본 wav, 마디 길이(초), 마디 수, 저장할 파일
python3 tools/sound/sfx_class.py --one answer_ding 2 ding2.wav          # 교실 · 예능 효과음 하나(전부는 인자 없이 → tools/sound/out/sfx_class/)
```
- 끝 화면 음악은 '왕관이 내려오는 순간'과 '다음 섬에 불이 켜지는 순간'에 반짝 소리를 맞춥니다. 저장소의 파일은 시안으로 만든 대표 판입니다.
- `bgm.py`는 두근두근러닝 제작 폴더에서 영상의 대사 구간에 맞춰 섞는 스크립트라 그대로는 돌지 않습니다. 토막을 만드는 부분(`section()`)을 참고하세요.
- `model_kepler/`의 두 파일은 원본에서 불러오는 경로와 저장 폴더만 저장소에 맞게 바꿨습니다.

라이선스: 저장소 전체와 같은 CC BY-NC 4.0 — 출처 「두근두근러닝(greatsong)」. 단 `zzfx.py`의 원본 ZzFX 부분은 MIT 라이선스(파일 안 고지)를 따릅니다.
