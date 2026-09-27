# CATALOGS — реестр каталогов производителей

| ID | Производитель | Изделия | Исходник | Компиляция .md | JSON (code-first) | Состояние |
|---|---|---|---|---|---|---|
| CAT-01 | HIWIN | рельсы и каретки серии HG (G99TE17-1306) | [docs/HG-Series-Catalog_opt.pdf](../docs/HG-Series-Catalog_opt.pdf) | [docs/HG-Series-Catalog_opt.md](../docs/HG-Series-Catalog_opt.md) | specs/catalog_hiwin_hg.json (CP-02) | .md есть, парсер — CP-02 |

Правила: PDF — первоисточник; .md — дословная компиляция (объединённые ячейки
раскрыты); JSON строится только парсером из .md, руками не правится.
Каталожный номер пары рельс+каретка присваивает парсер (формат — OQ-03).

Наличие и цена — [vendor_prices.json](vendor_prices.json), заполняет заказчик:
ключ — каталожный номер или обозначение HIWIN; `price` за шт (каретка)
или за метр (`unit: "m"`, рельс); `available`, `lead_days`, `supplier`, `date`.
Позиция без цены попадает в отчёт `out/cost_missing.md` (CP-03).
