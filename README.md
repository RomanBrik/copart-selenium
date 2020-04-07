# Selenium based parser of 'copart.com' website
Put the Chrome driver into root
## Requirements
1. Selenium
2. Lxml
## Usage: 
```
usage: main.py [-h] [-u URL] [-q QUERY] [-f FILTERS] [--photos] [--seller]
`Copart` parser. Parse car lots with images!

optional arguments:
  -h, --help            show this help message and exit
  -u URL, --url URL     Specify the url
  -q QUERY, --query QUERY
                        Write your model. For example: `honda accord`
  -f FILTERS, --filters FILTERS
                        Choose the filters
  --photos              Download photos to lot
  --seller              Download lot if has a seller
```

## Examples

1. `python main.py -q 'Bmw m3' -f 'Run and Drive,Buy It Now,2018,2016' --seller --photos`
2. `python main.py -u 'https://www.copart.com/lotSearchResults/?free=true&query=bmw%20m3' -f 'Run and Drive,Buy It Now'`
