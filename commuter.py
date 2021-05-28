import getopt
import sys

import requests
from bs4 import BeautifulSoup
import json
import lxml
import pickle
import os
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

debug = False
url = 'https://www.canyon.com/fr-fr/outlet-bikes/?cgid=outlet&prefn1=pc_familie&prefn2=pc_rahmengroesse&prefv1=Commuter&prefv2=M&searchType=outlet'


def parse_page(html):
    bikes_found = []
    soup = BeautifulSoup(html, 'lxml')
    myli = soup.find_all("li", {"class": "productGrid__listItem"})
    for li in myli:
        div = li.find("div", {"class": "productTile"})
        bike_dict = json.loads(div['data-gtm-impression'])
        bike = bike_dict['ecommerce']['impressions'][0]
        if debug:
            print(
            f"Bike found! :\n\t-id : {bike['id']}\n\t-Name (year) : {bike['name']} ({bike['dimension50']})\n\t-size : {bike['dimension53']}\n\t-price : {bike['metric4']} instead of {bike['metric5']}")
        bikes_found.append(
            {"name": bike['name'], "year": bike['dimension50'], "id": bike['id'], "size": bike['dimension53'],
             'outlet_price': bike['metric4'], 'normal_price': bike['metric5']})
    return bikes_found


def read_html_file(filename):
    with open(filename, 'r', encoding="utf8") as f:
        print(filename)
        contents = f.read()
        return contents


def save_parsed_results(results,save='current_bikes.pkl'):
    """return new ones only"""
    if os.path.exists(save):
        with open(save, 'rb') as f:
            past_results = pickle.load(f)
            past_results_ids = [bike['id'] for bike in past_results]
            # get new ones
            new_ones = []
            for bike in results:
                if bike['id'] not in past_results_ids:
                    new_ones.append(bike)
            if len(new_ones) > 0 and debug:
                print(f"Found {len(new_ones)} new bikes :")
                print(new_ones)
    else:
        new_ones = results
        if len(results) > 0:
            print(f"Found {len(new_ones)} new bikes :")
            print(new_ones)
    # save results
    with open(save, 'wb') as f:
        pickle.dump(results, f)
    return new_ones


def email_new_bikes(new_bikes,
                    sender_email=None,
                    password=None,
                    receiver_email=None,
                    smtp_server=None,
                    smtp_port=None):
    # Try to log in to server and send email
    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.set_debuglevel(1)
        server.connect(smtp_server)
        server.ehlo()
        server.login(sender_email, password)  # On s'authentifie
        # Create message
        message = ""
        message += f"Nombre de nouveau(x) vélo(s) : {len(new_bikes)}\n"
        for bike in new_bikes:
            message += "==============================================================\n"
            message += f"\t-id : {bike['id']}\n\t-Name (year) : {bike['name']} ({bike['year']})\n\t-size : {bike['size']}\n\t-price : {bike['outlet_price']} instead of {bike['normal_price']}\n"
        message += "==============================================================\n"
        message += f"<a href=\"{url}\">Aller à l'outlet</a>"

        if debug:
            print(f"Sending following message : \n {message}\n")
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = 'Nouveaux vélos sur le site Outlet de Canyon!'
        msg.attach(MIMEText(message))
        server.sendmail(sender_email, receiver_email, msg.as_string())
    except Exception as e:
        # Print any error messages to stdout
        print(e)
    finally:
        server.quit()


def do_operation(save_file='current_bikes.pkl',
                 sender_email=None,
                 password=None,
                 receiver_email=None,
                 smtp_server=None,
                 smtp_port=None):
    r = requests.get(url)
    parsed_results = parse_page(r.text)
    new_bikes = save_parsed_results(parsed_results, save_file)
    if len(new_bikes) > 0:
        email_new_bikes(new_bikes,
                        sender_email=sender_email,
                        password=password,
                        receiver_email=receiver_email,
                        smtp_server=smtp_server,
                        smtp_port=smtp_port)

def usage():
    print('Usage: \npython commuter.py '
          '--smtp_server=smtp.mydomain.fr '
          '--port=465 '
          '--sender_email=myemail@mydomain.fr '
          '--password=XXX '
          '--receiver_email=youremail@otherdomain.fr')


if __name__ == '__main__':
    sender_email = None
    password = None
    receiver_email = None
    smtp_server = None
    smtp_port = None
    save_output_file='current_bikes.pkl'

    try:
        opts, args = getopt.getopt(sys.argv[1:], "S:P:s:p:r:o:", ["smtp_server=", "port=", 'sender_email=', 'password=', 'receiver_email=', 'output='])
    except getopt.GetoptError as e:
        print(e)
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-S", "--smtp_server"):
            smtp_server = arg
        elif opt in ["-P", "--port"]:
            smtp_port = arg
        elif opt in ["-s", "--sender_email"]:
            sender_email = arg
        elif opt in ["-p", "--password"]:
            password = arg
        elif opt in ["-P", "--receiver_email"]:
            receiver_email = arg
        elif opt in ["-o", "--output"]:
            save_output_file = arg

    if sender_email is None:
        print("Missing sender email")
        usage()
        sys.exit()
    elif password is None:
        print("Missing sender password")
        usage()
        sys.exit()
    elif receiver_email is None:
        print("Missing receiver email")
        usage()
        sys.exit()
    elif smtp_server is None:
        print("Missing SMTP server address")
        usage()
        sys.exit()
    elif smtp_port is None:
        print("Missing SMTP server port (SSL only)")
        usage()
        sys.exit()
    else:
        do_operation(save_file=save_output_file,
                     sender_email=sender_email,
                     password=password,
                     receiver_email=receiver_email,
                     smtp_server=smtp_server,
                     smtp_port=smtp_port)
