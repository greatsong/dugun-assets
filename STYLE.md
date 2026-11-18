# 그림체 기준과 프롬프트 틀

이 저장소에 어울리는 새 그림을 만들 때, 그림체를 통일하기 위해 지키는 기준입니다.

## 1. 그림체
- **굵은 검은 외곽선 + 파스텔 단색 면 + 둥글고 귀여운 모양.** 출연 캐릭터와 같은 그림체입니다.
- **그림 안에는 글자 · 숫자 · 로고 · 상표 · 실존 인물을 넣지 않습니다.** 글자가 필요하면 영상이나 문서에서 따로 얹습니다.
  (예외: 캐릭터 셈셈의 계산기 화면 숫자 `21`, 째깍의 시계 바늘은 캐릭터 디자인의 일부입니다.)
- **배경**은 가운데를 비우고 디테일을 가장자리에 둡니다. 배경에는 사람이나 캐릭터를 그리지 않습니다. 캐릭터는 그 위에 따로 세웁니다.
- **소품**은 한 장에 물건 하나만, 흰 바탕 가운데에 그립니다. 생성한 뒤 바깥쪽 흰 배경만 지워 투명하게 만듭니다.
- 색상은 남색 · 크림색 · 아이보리색 · 산호색 · 하늘색 · 연보라색 · 금색과 어울리는 차분한 파스텔 톤을 씁니다. 너무 센 원색은 피합니다.
- 그리지 않는 요소: 적십자와 비슷한 십자가(초록색 하트 등으로 대체), 해골 · 무기, 다른 작품의 캐릭터나 탈것.

## 2. 캐릭터 참고 그림
새 그림을 그릴 때는 **출연 캐릭터 그림을 '참고 그림'으로 함께 보냅니다.** 그러면 AI 도구가 외곽선 굵기 · 색감 · 얼굴 모양을 비슷하게 맞춰 줍니다.
- 그림체 기준으로 쓰는 캐릭터: `char_dugeun`(두근), `char_arong`(아롱), `char_ttukttak`(뚝딱), `char_doran`(도란). 배경 · 소품에는 `char_dugeun` · `char_chorong`을 많이 씁니다.
- 프롬프트 끝에 "Do not draw the reference characters themselves"를 붙여, 참고 캐릭터가 그림에 끼어들지 않게 합니다.
- 같은 장소의 다른 모습을 그릴 때(예: 시간대가 다른 컬링 경기장)는 앞서 그린 배경을 참고 그림으로 함께 보냅니다.

## 3. 프롬프트 틀
프롬프트는 영어로 씁니다. 순서는 **[무엇을 그릴지] + [구도] + [그림체] + [색] + [금지]** 입니다.
실제 입력하는 프롬프트 = 공통 틀 + `" Subject: "` + 개별 그림 설명. `catalog.json`의 `prompt` 항목에는 이렇게 합친 전체 문장이 들어 있습니다.

공통 틀(두근두근러닝 도감 `cast_bible.js`에서 옮김):
- 배경: `Soft pastel flat illustration background in the same cute style as the references, simple shapes with gentle dark outlines, slightly muted and low-contrast so characters placed on top stand out, no characters, no faces, no text, no letters, 16:9.`
- 소품: `Draw ONE object (no face unless asked) in the same cute sticker style as the references: thick dark outline, flat pastel colors, centered, plain pure white background, no text.`
- 캐릭터: `Draw ONE character in EXACTLY the same art style as the reference characters: cute kawaii sticker illustration, thick dark brown-black outline, flat pastel colors with one soft shade tone, simple face with two small solid black oval eyes, a tiny curved smile, pink blush ovals on the cheeks, thin black stick arms and short stick legs. Full body, front view, centered, generous margin, plain pure white background, no shadow on the ground, no text, no letters.`

본문에 붙이는 문장:
- 배경 구도: "Wide 16:9 landscape background. Keep the center of the picture simple and mostly empty so characters and text can be placed on top; put the details along the top and bottom edges and the sides. Do not draw any characters or people."
- 소품 구도: "One single object, centered, on a plain white background, nothing else."
- 그림체: "Same drawing style as the reference characters: thick black outlines, flat pastel color fills, round soft cute shapes."
- 색: "Calm colors that suit a palette of navy, cream, ivory, coral, sky blue, lavender and gold."
- 금지: "Absolutely no letters, no numbers, no words, no logos, no brand marks, no real people anywhere in the picture."

본보기: `catalog.json`에서 `bg_clinic_school`(배경), `prop_test_kit`(소품), `char_haim`(캐릭터)의 `prompt`를 보면 됩니다.

## 4. 크기와 파일
- 배경: 1920×1080 jpg(품질 92). 끝 화면용 큰 배경 일부는 png입니다.
- 소품 · 캐릭터 · 효과: 배경이 투명한 png, 정사각형에 가까운 비율.
- 재질: 위에서 내려다본 정사각형 타일(가장자리까지 꽉 채움).
- 파일 이름: 영문 소문자 `종류_대상_변형` (`bg_` · `prop_` · `tex_` · `fx_` · `char_` · `icon_`).

## 5. 생성 후 확인할 점
그림 안에 글자가 섞여 들어갔는지, 소품 안쪽의 흰색이 배경과 함께 잘못 지워지지 않았는지, 십자가 · 센 원색이 없는지, 배경이 캐릭터나 글씨보다 눈에 띄지 않는지 확인합니다.
