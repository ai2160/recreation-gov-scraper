Recreation.gov Scraper
================

Notifies you when campsites in a park/recreation area you are interested is available for booking.

This project is under active development and any help fixing open issues or improving the project is greately appreciated.

Usage
-----

```bash
cp example.secrets.py secrets.py    # Make a real secrets.py file with mailgun credentials
vim secrets.py                      # Fill in the mailgun secrets
virtualenv --no-site-packages .     # Create a virtualenv
source bin/activate                 # Enter it
pip install -r requirements.txt     # Install python dependencies 
python scraper.py                   # Run the scraper
```
