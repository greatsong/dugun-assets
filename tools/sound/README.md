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

```bash
pip install numpy
python3 tools/sound/outro_synth.py A 8.0 10.4 a.wav        # 곡, 왕관 반짝(초), 종(초), 저장할 파일
python3 tools/sound/outro_synth2.py all 8.0 10.4 ./out     # D~I 전부
python3 tools/sound/model_kepler/sfx.py                    # → tools/sound/model_kepler/out/
python3 tools/sound/model_kepler/music.py A B              # → tools/sound/model_kepler/out/
```
- 끝 화면 음악은 '왕관이 내려오는 순간'과 '다음 섬에 불이 켜지는 순간'에 반짝 소리를 맞춥니다. 저장소의 파일은 시안으로 만든 대표 판입니다.
- `bgm.py`는 두근두근러닝 제작 폴더에서 영상의 대사 구간에 맞춰 섞는 스크립트라 그대로는 돌지 않습니다. 토막을 만드는 부분(`section()`)을 참고하세요.
- `model_kepler/`의 두 파일은 원본에서 불러오는 경로와 저장 폴더만 저장소에 맞게 바꿨습니다.

라이선스: 저장소 전체와 같은 CC BY-NC 4.0 — 출처 「두근두근러닝(greatsong)」.
