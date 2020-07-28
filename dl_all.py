import autotrader
import cars
import gumtree
import surf4cars
import os
import traceback
link_files = [
    # 'cars_links.txt',
    # 'surf4cars_links.txt',
    # 'gumtree_links.txt',
]

def main():
    for link in link_files:
        try:
            os.remove(link)
        except OSError as error:
            pass
    # try:
    #     print('\n\n==============================Downloading autotrader==============================\n\n')
    #     autotrader.main()
    # except Exception:
    #     traceback.print_exc()
    # try:
    #     print('\n\n==============================Downloading Cars==============================')
    #     cars.main()
    # except Exception:
    #     traceback.print_exc()
    # try:
    #     print('\n\n==============================Downloading gumtree==============================')
    #     gumtree.main()
    # except Exception:
    #     traceback.print_exc()
    try:
        print('\n\n==============================Downloading surf4cars==============================')
        surf4cars.main()
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    main()