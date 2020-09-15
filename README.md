# Wikipedia-Search-Engine

## Introduction
This is a wikipedia based search engine. The inverted index of Wikipedia data is made using Block Sort Based Indexing. The search takes approximately 0.5 seconds and retrieves the top 10 results via Tf-Idf ranking.

## Indexing

### Running the code
`pip install -r requirements.txt`

`python3 index.py [path to wiki dump] [path of index folder]`

Wiki dump should be in `.xml` format (Sample wiki dump is present with filename `enwiki-latest-pages-articles26.xml-p42567204p42663461`).
Index folder is the name of the folder where you want to store inverted index of the data. Sample index folder created by above dump is stored in `index`.


## Searching

### Running the code
`pip install -r requirements.txt`

`python3 search.py [path of index folder]`

`Enter your query when prompt appears`

Index folder should be created using above code.

### Field queries
This search engine supports plain queries as well as field queries.
Example of a plain query - `Mahatma Gandhi`. This query will retrieve all documents that contains the text `Mahatma Gandhi` anywhere in any document.
Example of a field query - `t:Mahatma c:Gandhi`. This query will retrieve all documents that have text `Mahatma` in the title of the document & `Gandhi` in the category of the document.

Supported fields are:
- t -> Title
- c -> Category
- e -> Extlink
- i -> Infobox
- r -> References
- b -> Body
