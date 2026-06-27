import requests
import json
from pathlib import Path
import time

COMPANY_JSON = Path("../../company.json")
URL_CT = "https://www.sec.gov/files/company_tickers.json"
COMPANY_DETAIL = "https://data.sec.gov/submissions/CIK{}.json"
DOWNLOAD_DATA = Path("../../data")
RATE_LIMIT_SECONDS = 0.125

def get(client,url): # "SEC will limit automated searches to a total of no more than 10 requests per second " from EDGAR News and Announcement
    response = client.get(url)
    response.raise_for_status()
    time.sleep(RATE_LIMIT_SECONDS)
    return response


with open(COMPANY_JSON,"r") as files: # open json file that contains company name and the ticker
    company_data = json.load(files)

def build_client(): # Build a requests session with the required SEC User-Agent header.
    session = requests.Session()
    session.headers.update({
        "User-Agent" : "epochsum@gmail.com"
    })
    return session

my_client = build_client()
ticker_response = get(my_client,URL_CT)
company_tickers = ticker_response.json()

def resolve_cik(ticker): # Convert ticker symbol to CIK.
    for value in company_tickers.values():
        if value["ticker"] == ticker.upper():
            cik = str(value["cik_str"])
            return( {
                "raw": cik,
                "padded": cik.zfill(10)  
            })
    raise ValueError("No company found with the ticker u input ")

def find_latest_10k(client,cik): # Fetch company submissions JSON and find the latest 10-K filing.
    url = COMPANY_DETAIL.format(cik)
    response = get(client,url)
    edgar = response.json()
    
    filings = edgar["filings"]["recent"]
    
    try:
        idx = filings["form"].index("10-K")
    except ValueError:
        raise ValueError("No 10-K file for this company")
    
    accession_number = filings["accessionNumber"][idx]
    accession_number = accession_number.replace("-","")

    primary_number = filings["primaryDocument"][idx]
    
    return({
        "ac": accession_number,
        "pd" : primary_number
    })

def build_document_url(cik,accession_number,primary_number): # Build the SEC archive URL for the filing document.
    finalurl = "https://www.sec.gov/Archives/edgar/data/{}/{}/{}"
    finalurl = finalurl.format(cik["raw"],accession_number,primary_number)
    return finalurl

def download(client, url, company_name, form, name_of_file): # make a file if it doesnt exist and write on what it received from the website html
    path = DOWNLOAD_DATA / company_name / form
    path.mkdir(parents=True,exist_ok=True)
    download_file = path/name_of_file
    if download_file.exists():
        return download_file
    response = get(client,url)
    with open(download_file,"wb") as files:
        files.write(response.content)
    return download_file


def main():
    for key, values in company_data.items():
        cik = resolve_cik(values["ticker"])
        filing = find_latest_10k(my_client,cik["padded"])
        url = build_document_url(cik,filing["ac"],filing["pd"])
        path = download(my_client,url,key,"10-K",filing["pd"])
        print(path)


if __name__ == "__main__":
    main()

