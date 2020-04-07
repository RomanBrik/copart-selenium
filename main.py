import argparse

from script import Copart


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='`Copart` parser. Parse car lots with images!')

    parser.add_argument('-u', '--url', action='store', default=None, help='Specify the url')
    parser.add_argument('-q', '--query', action='store', default=None, help='Write your model. For example: `honda accord`')
    parser.add_argument('-f', '--filters', type=str, default=[], help='Choose the filters')

    parser.add_argument('--photos', action='store_true', default=False, help='Download photos to lot')
    parser.add_argument('--seller', action='store_true', default=False, help='Download lot if has a seller')

    
    args = parser.parse_args()
    filters = args.filters

    if filters:
        filters = args.filters.split(",")

    c = Copart(query=args.query, url=args.url, filters=filters)
    c.scrape_lots(photos=args.photos, seller=args.seller)

