import urllib.request as req
import time
import datetime
import re
import pickle
from glob import glob
import os

from bs4 import BeautifulSoup


DATA_PATH = "data"
BASE_URL = "https://recipe.rakuten.co.jp"
CATEGORY_URL = "https://recipe.rakuten.co.jp/category"
DAYTIME = [9, 23]
TIME_ZONE_JST = datetime.timezone(datetime.timedelta(hours=9))

from typing import List
from dataclasses import dataclass

def process_text(text):
    # text = re.sub(r'[!-/:-@[-`{-~]', "", text)  # 半角記号
    # text = re.sub(r'[︰-＠]', "", text)  # 全角記号
    # text=re.sub(r'[☆]', "", text)#その他の全角記号
    text = re.sub('\n', " ", text)  # 改行文字
    return text


@dataclass
class IngredientsElement:
    name: str
    amount: str


@dataclass
class HowToElement:
    step: str
    text: str


@dataclass
class Recipe:
    name: str
    serve: str
    ingredients: List[IngredientsElement]
    how_to: List[HowToElement]


def get_soup(url):
    """
    urlにアクセスしhtmlを取得する。
    :param url:
    :return:
    """
    if DAYTIME[0] <= datetime.datetime.now(TIME_ZONE_JST).hour <= DAYTIME[-1]:
        time.sleep(3.0)  # 昼間は3秒スリープを入れる
    else:
        time.sleep(1.0)  # 夜間は1秒スリープを入れる
    res = req.urlopen(url)
    soup = BeautifulSoup(res, "html.parser")
    return soup


def get_category_url_list():
    """
    レシピのカテゴリー別URLを取得する
    :return:
    """
    soup = get_soup(CATEGORY_URL)
    category_source = soup.find_all(href=re.compile("(/category/).\d+-+\d+-+"))
    category_url_list = [tag.attrs["href"][:-1] for tag in category_source]
    return category_url_list


def execute_scraping(start_idx):
    recipe_names = set()  # 重複するレシピ排除のため
    category_url_list = get_category_url_list()
    for i in range(start_idx, len(category_url_list)):
        recipe_list = []
        if len(recipe_names) > 10000:
            recipe_names = set()
        soup = get_soup(BASE_URL + category_url_list[i])
        recipe_url_source = soup.find_all(href=re.compile("^(/recipe/)"))
        for recipe_url in recipe_url_source[:3]:
            soup = get_soup(BASE_URL + recipe_url.attrs["href"][:-1])
            recipe_name = str(soup.find(class_="page_title__text").contents[0])
            recipe_name = re.sub(r"レシピ・作り方", "", recipe_name)
            recipe_name = re.sub(r" ", "", recipe_name)
            recipe_name = process_text(recipe_name)
            if recipe_name not in recipe_names:
                print(recipe_name)
                recipe_names.add(recipe_name)
                serve = str(soup.find(class_="contents_title_mb").contents[0])[2:]
                ingredients_source = soup.find_all(class_="recipe_material__item")
                ingredients = []
                for ing in ingredients_source:
                    ing_name = process_text(ing.find(class_="recipe_material__item_name").text)
                    ing_amount = process_text(ing.find(class_="recipe_material__item_serving").text)
                    if ing_name and ing_amount:
                        ingredients.append(IngredientsElement(
                            ing_name,
                            ing_amount))

                how_to_source = soup.find_all(id="step_box_li")
                how_to = []
                for ht in how_to_source:
                    step = ht.find(class_=re.compile(r"(recipeNum)+"))
                    memo = ht.find(class_="stepMemo")
                    if step is not None and memo is not None:
                        how_to.append(HowToElement(
                            step.contents[0],
                            memo.contents[0]))
                recipe_list.append(Recipe(
                    recipe_name,
                    serve,
                    ingredients,
                    how_to))

        os.makedirs(DATA_PATH, exist_ok=True)
        with open(file=f"{DATA_PATH}/recipe_list_{i}.pkl", mode="wb") as f:
            pickle.dump(recipe_list, f)


def main():
    start_idx = len(glob("data/*"))
    execute_scraping(start_idx)


if __name__ == "__main__":
    main()
