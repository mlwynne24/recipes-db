import json
from datetime import UTC, datetime

from sqlmodel import Field, Relationship, SQLModel


class Recipe(SQLModel, table=True):
    __tablename__ = "recipes"

    id: int | None = Field(default=None, primary_key=True)
    title: str
    url: str = Field(unique=True, index=True)
    description: str | None = None
    method: str | None = None
    tags: str | None = None  # JSON-serialized list of strings
    prep_time: str | None = None
    cook_time: str | None = None
    serves: str | None = None
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    ingredients: list["Ingredient"] = Relationship(back_populates="recipe")

    @property
    def tag_list(self) -> list[str]:
        return json.loads(self.tags) if self.tags else []

    @tag_list.setter
    def tag_list(self, value: list[str]) -> None:
        self.tags = json.dumps(value)


class Ingredient(SQLModel, table=True):
    __tablename__ = "ingredients"

    id: int | None = Field(default=None, primary_key=True)
    recipe_id: int = Field(foreign_key="recipes.id", index=True)
    name: str = Field(index=True)  # normalized: "chicken breast"
    quantity: str | None = None
    unit: str | None = None
    original_text: str

    recipe: Recipe | None = Relationship(back_populates="ingredients")
