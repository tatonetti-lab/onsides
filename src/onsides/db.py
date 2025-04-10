import enum

from sqlmodel import Field, Relationship, SQLModel

# Primary tables


class DrugLabelSource(str, enum.Enum):
    US = "US"
    UK = "UK"
    EU = "EU"
    JP = "JP"


class DrugLabelSection(str, enum.Enum):
    AE = "AE"  # Adverse effects
    WP = "WP"  # Warnings and precautions
    BW = "BW"  # Boxed warnings
    NA = "NA"  # Not applicable (non-US drug labels)


class MatchMethod(str, enum.Enum):
    SM = "SM"  # String match only
    PMB = "PMB"  # String match + PubMedBERT


class ProductToRxNorm(SQLModel, table=True):
    __tablename__: str = "product_to_rxnorm"  # type: ignore

    label_id: int | None = Field(
        default=None, foreign_key="product_label.label_id", primary_key=True
    )
    rxnorm_product_id: str | None = Field(
        default=None, foreign_key="vocab_rxnorm_product.rxnorm_id", primary_key=True
    )


class ProductLabel(SQLModel, table=True):
    __tablename__: str = "product_label"  # type: ignore

    label_id: int | None = Field(default=None, primary_key=True)
    source: DrugLabelSource
    source_product_name: str
    source_product_id: str
    source_label_url: str | None

    rxnorm_products: list["RxNormProduct"] = Relationship(
        back_populates="labels", link_model=ProductToRxNorm
    )
    adverse_effects: list["AdverseEffect"] = Relationship(
        back_populates="product_label"
    )


class AdverseEffect(SQLModel, table=True):
    __tablename__: str = "product_adverse_effect"  # type: ignore

    product_label_id: int | None = Field(
        default=None, foreign_key="product_label.label_id"
    )
    effect_id: int | None = Field(default=None, primary_key=True)
    label_section: DrugLabelSection
    effect_meddra_id: int | None = Field(
        default=None, foreign_key="vocab_meddra_adverse_effect.meddra_id"
    )
    match_method: MatchMethod
    pred0: float | None = None
    pred1: float | None = None

    product_label: ProductLabel = Relationship(back_populates="adverse_effects")
    effect_meddra: "MedDraAdverseEffect" = Relationship(
        back_populates="label_adverse_effects"
    )


# Reference tables


class MedDraAdverseEffect(SQLModel, table=True):
    __tablename__: str = "vocab_meddra_adverse_effect"  # type: ignore

    meddra_id: int = Field(primary_key=True)
    meddra_name: str
    meddra_term_type: str

    label_adverse_effects: list[AdverseEffect] = Relationship(
        back_populates="effect_meddra"
    )


class RxNormIngredientToProduct(SQLModel, table=True):
    __tablename__: str = "vocab_rxnorm_ingredient_to_product"  # type: ignore

    ingredient_id: str | None = Field(
        default=None, foreign_key="vocab_rxnorm_ingredient.rxnorm_id", primary_key=True
    )
    product_id: str | None = Field(
        default=None, foreign_key="vocab_rxnorm_product.rxnorm_id", primary_key=True
    )


class RxNormIngredient(SQLModel, table=True):
    __tablename__: str = "vocab_rxnorm_ingredient"  # type: ignore

    rxnorm_id: str = Field(primary_key=True)
    rxnorm_name: str
    rxnorm_term_type: str

    products: list["RxNormProduct"] = Relationship(
        back_populates="ingredients", link_model=RxNormIngredientToProduct
    )


class RxNormProduct(SQLModel, table=True):
    __tablename__: str = "vocab_rxnorm_product"  # type: ignore

    rxnorm_id: str = Field(primary_key=True)
    rxnorm_name: str
    rxnorm_term_type: str

    ingredients: list[RxNormIngredient] = Relationship(
        back_populates="products", link_model=RxNormIngredientToProduct
    )
    labels: list[ProductLabel] = Relationship(
        back_populates="rxnorm_products", link_model=ProductToRxNorm
    )
