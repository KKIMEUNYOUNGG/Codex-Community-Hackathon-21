from __future__ import annotations

from enum import Enum


TAXONOMY_VERSION = "fashion-aspect-v2"


class AspectCategory(str, Enum):
    SIZE_FIT = "SIZE_FIT"
    MATERIAL = "MATERIAL"
    COLOR = "COLOR"
    DESIGN = "DESIGN"
    COMFORT_FUNCTION = "COMFORT_FUNCTION"
    QUALITY_DURABILITY = "QUALITY_DURABILITY"
    TRANSPARENCY = "TRANSPARENCY"
    CARE = "CARE"
    PRICE_VALUE = "PRICE_VALUE"


class Aspect(str, Enum):
    OVERALL_SIZE = "OVERALL_SIZE"
    LENGTH = "LENGTH"
    SLEEVE_LENGTH = "SLEEVE_LENGTH"
    SHOULDER = "SHOULDER"
    CHEST = "CHEST"
    WAIST = "WAIST"
    THIGH = "THIGH"
    SILHOUETTE = "SILHOUETTE"
    TOUCH = "TOUCH"
    THICKNESS = "THICKNESS"
    STRETCH = "STRETCH"
    WEIGHT = "WEIGHT"
    BREATHABILITY = "BREATHABILITY"
    WARMTH = "WARMTH"
    COLOR = "COLOR"
    DESIGN = "DESIGN"
    COMFORT = "COMFORT"
    FUNCTIONALITY = "FUNCTIONALITY"
    QUALITY = "QUALITY"
    DURABILITY = "DURABILITY"
    TRANSPARENCY = "TRANSPARENCY"
    CARE = "CARE"
    PRICE_VALUE = "PRICE_VALUE"


class OpinionCode(str, Enum):
    GOOD_OVERALL = "GOOD_OVERALL"
    TRUE_TO_SIZE = "TRUE_TO_SIZE"
    FLATTERING_FIT = "FLATTERING_FIT"
    GOOD_LENGTH = "GOOD_LENGTH"
    SOFT = "SOFT"
    COMFORTABLE = "COMFORTABLE"
    LIGHTWEIGHT = "LIGHTWEIGHT"
    BREATHABLE = "BREATHABLE"
    WARM = "WARM"
    STRETCHY = "STRETCHY"
    GOOD_COLOR = "GOOD_COLOR"
    GOOD_DESIGN = "GOOD_DESIGN"
    FUNCTIONAL = "FUNCTIONAL"
    GOOD_QUALITY = "GOOD_QUALITY"
    DURABLE = "DURABLE"
    OPAQUE = "OPAQUE"
    EASY_CARE = "EASY_CARE"
    GOOD_VALUE = "GOOD_VALUE"
    OTHER_POSITIVE = "OTHER_POSITIVE"
    TOO_LARGE = "TOO_LARGE"
    TOO_SMALL = "TOO_SMALL"
    TOO_LONG = "TOO_LONG"
    TOO_SHORT = "TOO_SHORT"
    TOO_TIGHT = "TOO_TIGHT"
    TOO_LOOSE = "TOO_LOOSE"
    UNFLATTERING_FIT = "UNFLATTERING_FIT"
    ROUGH = "ROUGH"
    TOO_THICK = "TOO_THICK"
    TOO_THIN = "TOO_THIN"
    NOT_STRETCHY = "NOT_STRETCHY"
    TOO_HEAVY = "TOO_HEAVY"
    NOT_BREATHABLE = "NOT_BREATHABLE"
    NOT_WARM = "NOT_WARM"
    COLOR_MISMATCH = "COLOR_MISMATCH"
    COLOR_FADES = "COLOR_FADES"
    DESIGN_DISSATISFACTION = "DESIGN_DISSATISFACTION"
    UNCOMFORTABLE = "UNCOMFORTABLE"
    FUNCTIONALITY_ISSUE = "FUNCTIONALITY_ISSUE"
    DEFECT = "DEFECT"
    POOR_FINISH = "POOR_FINISH"
    NOT_DURABLE = "NOT_DURABLE"
    TRANSPARENT = "TRANSPARENT"
    SHRINKS = "SHRINKS"
    PILLS = "PILLS"
    DYE_TRANSFER = "DYE_TRANSFER"
    HARD_TO_CARE = "HARD_TO_CARE"
    OVERPRICED = "OVERPRICED"
    LOW_VALUE = "LOW_VALUE"
    OTHER_NEGATIVE = "OTHER_NEGATIVE"


POSITIVE_OPINION_CODES = frozenset(
    {
        OpinionCode.GOOD_OVERALL,
        OpinionCode.TRUE_TO_SIZE,
        OpinionCode.FLATTERING_FIT,
        OpinionCode.GOOD_LENGTH,
        OpinionCode.SOFT,
        OpinionCode.COMFORTABLE,
        OpinionCode.LIGHTWEIGHT,
        OpinionCode.BREATHABLE,
        OpinionCode.WARM,
        OpinionCode.STRETCHY,
        OpinionCode.GOOD_COLOR,
        OpinionCode.GOOD_DESIGN,
        OpinionCode.FUNCTIONAL,
        OpinionCode.GOOD_QUALITY,
        OpinionCode.DURABLE,
        OpinionCode.OPAQUE,
        OpinionCode.EASY_CARE,
        OpinionCode.GOOD_VALUE,
        OpinionCode.OTHER_POSITIVE,
    }
)
NEGATIVE_OPINION_CODES = frozenset(set(OpinionCode) - set(POSITIVE_OPINION_CODES))


CATEGORY_ASPECTS: dict[AspectCategory, frozenset[Aspect]] = {
    AspectCategory.SIZE_FIT: frozenset(
        {
            Aspect.OVERALL_SIZE,
            Aspect.LENGTH,
            Aspect.SLEEVE_LENGTH,
            Aspect.SHOULDER,
            Aspect.CHEST,
            Aspect.WAIST,
            Aspect.THIGH,
            Aspect.SILHOUETTE,
        }
    ),
    AspectCategory.MATERIAL: frozenset(
        {
            Aspect.TOUCH,
            Aspect.THICKNESS,
            Aspect.STRETCH,
            Aspect.WEIGHT,
            Aspect.BREATHABILITY,
            Aspect.WARMTH,
        }
    ),
    AspectCategory.COLOR: frozenset({Aspect.COLOR}),
    AspectCategory.DESIGN: frozenset({Aspect.DESIGN}),
    AspectCategory.COMFORT_FUNCTION: frozenset({Aspect.COMFORT, Aspect.FUNCTIONALITY}),
    AspectCategory.QUALITY_DURABILITY: frozenset({Aspect.QUALITY, Aspect.DURABILITY}),
    AspectCategory.TRANSPARENCY: frozenset({Aspect.TRANSPARENCY}),
    AspectCategory.CARE: frozenset({Aspect.CARE}),
    AspectCategory.PRICE_VALUE: frozenset({Aspect.PRICE_VALUE}),
}


ALL_ASPECTS = frozenset(Aspect)
FIT_WIDTH_ASPECTS = frozenset(
    {
        Aspect.OVERALL_SIZE,
        Aspect.SHOULDER,
        Aspect.CHEST,
        Aspect.WAIST,
        Aspect.THIGH,
        Aspect.SILHOUETTE,
    }
)
OPINION_ALLOWED_ASPECTS: dict[OpinionCode, frozenset[Aspect]] = {
    OpinionCode.GOOD_OVERALL: ALL_ASPECTS,
    OpinionCode.TRUE_TO_SIZE: frozenset({Aspect.OVERALL_SIZE}),
    OpinionCode.FLATTERING_FIT: FIT_WIDTH_ASPECTS,
    OpinionCode.GOOD_LENGTH: frozenset({Aspect.LENGTH, Aspect.SLEEVE_LENGTH}),
    OpinionCode.SOFT: frozenset({Aspect.TOUCH}),
    OpinionCode.COMFORTABLE: frozenset({Aspect.COMFORT}),
    OpinionCode.LIGHTWEIGHT: frozenset({Aspect.WEIGHT}),
    OpinionCode.BREATHABLE: frozenset({Aspect.BREATHABILITY}),
    OpinionCode.WARM: frozenset({Aspect.WARMTH}),
    OpinionCode.STRETCHY: frozenset({Aspect.STRETCH}),
    OpinionCode.GOOD_COLOR: frozenset({Aspect.COLOR}),
    OpinionCode.GOOD_DESIGN: frozenset({Aspect.DESIGN}),
    OpinionCode.FUNCTIONAL: frozenset({Aspect.FUNCTIONALITY}),
    OpinionCode.GOOD_QUALITY: frozenset({Aspect.QUALITY}),
    OpinionCode.DURABLE: frozenset({Aspect.DURABILITY}),
    OpinionCode.OPAQUE: frozenset({Aspect.TRANSPARENCY}),
    OpinionCode.EASY_CARE: frozenset({Aspect.CARE}),
    OpinionCode.GOOD_VALUE: frozenset({Aspect.PRICE_VALUE}),
    OpinionCode.OTHER_POSITIVE: ALL_ASPECTS,
    OpinionCode.TOO_LARGE: FIT_WIDTH_ASPECTS,
    OpinionCode.TOO_SMALL: FIT_WIDTH_ASPECTS,
    OpinionCode.TOO_LONG: frozenset({Aspect.LENGTH, Aspect.SLEEVE_LENGTH}),
    OpinionCode.TOO_SHORT: frozenset({Aspect.LENGTH, Aspect.SLEEVE_LENGTH}),
    OpinionCode.TOO_TIGHT: FIT_WIDTH_ASPECTS,
    OpinionCode.TOO_LOOSE: FIT_WIDTH_ASPECTS,
    OpinionCode.UNFLATTERING_FIT: FIT_WIDTH_ASPECTS,
    OpinionCode.ROUGH: frozenset({Aspect.TOUCH}),
    OpinionCode.TOO_THICK: frozenset({Aspect.THICKNESS}),
    OpinionCode.TOO_THIN: frozenset({Aspect.THICKNESS}),
    OpinionCode.NOT_STRETCHY: frozenset({Aspect.STRETCH}),
    OpinionCode.TOO_HEAVY: frozenset({Aspect.WEIGHT}),
    OpinionCode.NOT_BREATHABLE: frozenset({Aspect.BREATHABILITY}),
    OpinionCode.NOT_WARM: frozenset({Aspect.WARMTH}),
    OpinionCode.COLOR_MISMATCH: frozenset({Aspect.COLOR}),
    OpinionCode.COLOR_FADES: frozenset({Aspect.COLOR}),
    OpinionCode.DESIGN_DISSATISFACTION: frozenset({Aspect.DESIGN}),
    OpinionCode.UNCOMFORTABLE: frozenset({Aspect.COMFORT}),
    OpinionCode.FUNCTIONALITY_ISSUE: frozenset({Aspect.FUNCTIONALITY}),
    OpinionCode.DEFECT: frozenset({Aspect.QUALITY}),
    OpinionCode.POOR_FINISH: frozenset({Aspect.QUALITY}),
    OpinionCode.NOT_DURABLE: frozenset({Aspect.DURABILITY}),
    OpinionCode.TRANSPARENT: frozenset({Aspect.TRANSPARENCY}),
    OpinionCode.SHRINKS: frozenset({Aspect.CARE}),
    OpinionCode.PILLS: frozenset({Aspect.CARE}),
    OpinionCode.DYE_TRANSFER: frozenset({Aspect.CARE}),
    OpinionCode.HARD_TO_CARE: frozenset({Aspect.CARE}),
    OpinionCode.OVERPRICED: frozenset({Aspect.PRICE_VALUE}),
    OpinionCode.LOW_VALUE: frozenset({Aspect.PRICE_VALUE}),
    OpinionCode.OTHER_NEGATIVE: ALL_ASPECTS,
}


ASPECT_LABELS_KO: dict[Aspect, str] = {
    Aspect.OVERALL_SIZE: "전체 사이즈",
    Aspect.LENGTH: "총장",
    Aspect.SLEEVE_LENGTH: "소매 길이",
    Aspect.SHOULDER: "어깨 핏",
    Aspect.CHEST: "가슴 핏",
    Aspect.WAIST: "허리 핏",
    Aspect.THIGH: "허벅지 핏",
    Aspect.SILHOUETTE: "실루엣",
    Aspect.TOUCH: "소재 촉감",
    Aspect.THICKNESS: "소재 두께",
    Aspect.STRETCH: "신축성",
    Aspect.WEIGHT: "무게",
    Aspect.BREATHABILITY: "통기성",
    Aspect.WARMTH: "보온성",
    Aspect.COLOR: "색상",
    Aspect.DESIGN: "디자인",
    Aspect.COMFORT: "착용감",
    Aspect.FUNCTIONALITY: "기능성",
    Aspect.QUALITY: "품질·마감",
    Aspect.DURABILITY: "내구성",
    Aspect.TRANSPARENCY: "비침",
    Aspect.CARE: "세탁·관리",
    Aspect.PRICE_VALUE: "가격·가성비",
}


OPINION_LABELS_KO: dict[OpinionCode, str] = {
    OpinionCode.GOOD_OVERALL: "전반적으로 만족",
    OpinionCode.TRUE_TO_SIZE: "정사이즈",
    OpinionCode.FLATTERING_FIT: "핏이 좋음",
    OpinionCode.GOOD_LENGTH: "길이가 적절함",
    OpinionCode.SOFT: "부드러움",
    OpinionCode.COMFORTABLE: "편안함",
    OpinionCode.LIGHTWEIGHT: "가벼움",
    OpinionCode.BREATHABLE: "통기성이 좋음",
    OpinionCode.WARM: "보온성이 좋음",
    OpinionCode.STRETCHY: "신축성이 좋음",
    OpinionCode.GOOD_COLOR: "색상이 좋음",
    OpinionCode.GOOD_DESIGN: "디자인이 좋음",
    OpinionCode.FUNCTIONAL: "기능이 유용함",
    OpinionCode.GOOD_QUALITY: "품질이 좋음",
    OpinionCode.DURABLE: "내구성이 좋음",
    OpinionCode.OPAQUE: "비침이 적음",
    OpinionCode.EASY_CARE: "관리가 쉬움",
    OpinionCode.GOOD_VALUE: "가성비가 좋음",
    OpinionCode.OTHER_POSITIVE: "기타 긍정",
    OpinionCode.TOO_LARGE: "너무 큼",
    OpinionCode.TOO_SMALL: "너무 작음",
    OpinionCode.TOO_LONG: "너무 김",
    OpinionCode.TOO_SHORT: "너무 짧음",
    OpinionCode.TOO_TIGHT: "너무 타이트함",
    OpinionCode.TOO_LOOSE: "너무 헐렁함",
    OpinionCode.UNFLATTERING_FIT: "핏이 아쉬움",
    OpinionCode.ROUGH: "촉감이 거침",
    OpinionCode.TOO_THICK: "너무 두꺼움",
    OpinionCode.TOO_THIN: "너무 얇음",
    OpinionCode.NOT_STRETCHY: "신축성이 부족함",
    OpinionCode.TOO_HEAVY: "너무 무거움",
    OpinionCode.NOT_BREATHABLE: "통기성이 부족함",
    OpinionCode.NOT_WARM: "보온성이 부족함",
    OpinionCode.COLOR_MISMATCH: "색상이 기대와 다름",
    OpinionCode.COLOR_FADES: "색 빠짐",
    OpinionCode.DESIGN_DISSATISFACTION: "디자인이 아쉬움",
    OpinionCode.UNCOMFORTABLE: "착용감이 불편함",
    OpinionCode.FUNCTIONALITY_ISSUE: "기능이 불편함",
    OpinionCode.DEFECT: "불량",
    OpinionCode.POOR_FINISH: "마감이 미흡함",
    OpinionCode.NOT_DURABLE: "내구성이 부족함",
    OpinionCode.TRANSPARENT: "비침이 있음",
    OpinionCode.SHRINKS: "세탁 후 수축",
    OpinionCode.PILLS: "보풀 발생",
    OpinionCode.DYE_TRANSFER: "이염 발생",
    OpinionCode.HARD_TO_CARE: "관리가 어려움",
    OpinionCode.OVERPRICED: "가격이 비쌈",
    OpinionCode.LOW_VALUE: "가성비가 낮음",
    OpinionCode.OTHER_NEGATIVE: "기타 불만",
}


TAXONOMY_PROMPT = """
- SIZE_FIT: OVERALL_SIZE(전체 사이즈), LENGTH(총장), SLEEVE_LENGTH(소매),
  SHOULDER(어깨), CHEST(가슴), WAIST(허리), THIGH(허벅지), SILHOUETTE(실루엣/핏 모양)
- MATERIAL: TOUCH(촉감), THICKNESS(두께), STRETCH(신축성), WEIGHT(무게),
  BREATHABILITY(통기성), WARMTH(보온성)
- COLOR: COLOR
- DESIGN: DESIGN
- COMFORT_FUNCTION: COMFORT(착용감), FUNCTIONALITY(기능/활동성/주머니 등)
- QUALITY_DURABILITY: QUALITY(봉제·마감·불량), DURABILITY(내구성/손상)
- TRANSPARENCY: TRANSPARENCY(비침)
- CARE: CARE(세탁·수축·보풀·이염 등 관리)
- PRICE_VALUE: PRICE_VALUE(가격·가성비)
""".strip()
