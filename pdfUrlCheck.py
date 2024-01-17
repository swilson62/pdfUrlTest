#!/usr/bin/env python
"""
###################################################################################################
This file is part of `PDF URL Checker`.

`PDF URL Checker` is free software: you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

`PDF URL Checker` is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with PDF URL Test. If not, see
<https://www.gnu.org/licenses/>.  
###################################################################################################

Program Name: PDF URL Checker

pdfUrlCheck.py - Python script to scrape & verify URLs from PDF files in given directory

changeLog(v1.00-beta02):
    - Added check for links already tested to avoid adding them to currPdfLinks in scrape().
    - Fixed link count by incrementing linkNum before uri check. This means all links are counted
    now, even internal links.
    - Added code to write results to CSV file.
    - Fixed bug where URI's were written incorrectly by changing the csv dialect to `unix`.

Thoughts:
    - Need to clean up, update `ReadMe.md` & release `v1.00` final release.
    - If length of switches equals 2, and second switch is integer.....
    - Might be interesting to also add command line switch for timeout.

Attributions:
    - Knowledge required for concurrency to work well came from:
    https://superfastpython.com/.
    - The `requests` library. To install do `pip install requests==2.31.0`. See:
    https://pypi.org/project/requests/.
    - The `PyMuPDF` library. Ti install do `pip install PyMuPDF==1.23.8`. See:
    https://pypi.org/project/PyMuPDF/
    Kinda seems like this library is using code from the `fitz` library
    (https://github.com/pymupdf/PyMuPDF) internally without the library being installed locally.
    Install unneeded. See:
    https://pymupdf.readthedocs.io/en/latest/how-to-open-a-file.html
"""
   

# Python imports
import os
import sys
import csv
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
import requests

# Third party imports 
import fitz


def linkTest(currLinkToTest):
    """
    Define function to test links given a link to test
    """
    
    # Define variable required to control HTTP retries
    running = True
    retries = int(sys.argv[2])
    
    # Iterate thru retries for link test updating currLinkToTest with results
    for i in range(retries):
        while running == True:
            try:
                navTest = requests.get(currLinkToTest['linkPointsTo'], timeout = 10)
                if navTest.status_code == 200:
                    currLinkToTest.update({'linkStatus': 'Successful (Status: ' + \
                                    str(navTest.status_code) + ')'})
                else:
                    currLinkToTest.update({'linkStatus': 'Failed (Status: ' + \
                                    str(navTest.status_code) + ')'})
                    
                # On success, set conditions to exit iteration & break out of try loop
                if 'linkStatus' in currLinkToTest.keys():
                    running = False
                    i = retries-2
                    break
                    
            # On failure & retries exceeded, update with failure and exit loops
            except requests.exceptions.ConnectionError:
                if i > retries-2:
                    currLinkToTest.update({'linkStatus': 'Network Connection Error Occurred'})
                    running = False
                    i = retries-2
                    break

            except requests.exceptions.ReadTimeout:
                if i > retries-2:
                    currLinkToTest.update({'linkStatus': 'Read Timeout Error Occurred'})
                    running = False
                    i = retries-2
                    break

            except:
                if i > retries-2:
                    currLinkToTest.update({'linkStatus': 'Some Other Error Occurred'})
                    running = False
                    i = retries-2
                    break
            break

    # Return link test result
    return currLinkToTest


def scrape(currFile):
    """
    Define function for scraping of single PDF file given filename
    """
    
    # Define variables & notify user of status
    full_txt = ''
    print('Scraping {} ...'.format(currFile))
    currPdfLinks = []
    linksTested = []

    # Open file, Iterate thru pages, & extract links
    pdf = fitz.open(sys.argv[1] + os.path.sep + currFile)

    for page in pdf.pages():
        linkNum = 0
        for link in page.links():
            linkDict = {}
            linkNum+=1
            # If external HTTP link, append to link dictionary
            if 'uri' in link.keys() and link['uri'] not in linksTested:

                linkDict['fileName'] = currFile
                linkDict['pageInFile'] = page.number+1
                linkDict['linkNum'] = linkNum
                linkDict['linkType'] = 'HTTP Link'
                linkDict['linkPointsTo'] = link['uri']
                linksTested.append(link['uri'])
        
            if len(linkDict) != 0:
                currPdfLinks.append(linkDict)

    # Create thread pool with 20 workers
    with ThreadPool(20) as ourThreadPool:

        # Call threads for iterable fileList & wait for results
        navResults = ourThreadPool.map_async(linkTest, currPdfLinks)
        navResults.wait()

    # Return dict
    return navResults._value


def main():
    """
    Define main control function
    """
    
    # Local vars6
    pdfLinks = []
    fileList = []

    # Check command-line arguments
    if len(sys.argv) == 1:
        sys.argv.append('docs')
    if len(sys.argv) == 2:
        sys.argv.append('3')
    if len(sys.argv) != 3:
        sys.exit('Incorrect number of command line arguments. ' \
                 'Usage: pdfUrlCheck.py <doc_directory <num_of_http_retries>')
    if os.path.isdir(sys.argv[1]) == False:
        sys.exit('Directory does not exist. ' \
                 'Usage: pdfUrlCheck.py <doc_directory <num_of_http_retries>')
    
    # Check for improper timeout CLI argument
    try:
        int(sys.argv[2])
    except:
        sys.exit('Timeout not an integer. ' \
                 'Usage: pdfUrlCheck.py <doc_directory <num_of_http_retries>')

    if int(sys.argv[2]) < 1:
        sys.exit('Invalid timeout. ' \
                 'Usage: pdfUrlCheck.py <doc_directory <num_of_http_retries>')

    # Iterate files & if PDF file append to list for threads to iterate
    for iterFile in os.listdir(sys.argv[1]):
        if iterFile.endswith('.pdf'):
            fileList.append(iterFile)

    # Exit if no PDF files exist in specified directory
    if len(fileList) == 0:
        sys.exit("Directory specified contains no PDF files. Usage: urlDocScrape.py <doc_directory>")
            
    # Create multiprocessing pool with default number of processes
    with Pool() as pool:

        # Start processes for iterable fileList & wait for results
        currPdfLinks = pool.map_async(scrape, fileList)
        currPdfLinks.wait()

    # Iterate over results & append to doc_objects
    for currPdfLinks in currPdfLinks.get():
        pdfLinks.append(currPdfLinks)

    # Open `results.csv` for writing
    with open('results.csv', 'w', newline='') as csvResFile:
        csvWriter = csv.writer(csvResFile, dialect='unix')
        
        # Write column headers
        csvWriter.writerow(['Filename', 'Page Number', 'Link Number', 'Link Type', 'Link URI', \
                            'HTTP Status Code Result'])
    
        # Iterate thru pdfLinks and write results to `results.csv`.
        for docPdfLink in pdfLinks:
            for pdfLink in docPdfLink:
                csvWriter.writerow([pdfLink['fileName'], pdfLink['pageInFile'], pdfLink[
                    'linkNum'], pdfLink['linkType'], pdfLink[
                        'linkPointsTo'], pdfLink['linkStatus']])

    print(currPdfLinks)

# Initiate main()
if __name__ == "__main__":
    main()
