"""
spl_processor.py

Manages the downloading and pre-processing for the Structured Product
Labels (SPLs) for prescription drugs made available from DailyMed.

This script has two modes, the first is to process the Full Release of
prescription (rx) labels. Use this mode when initially setting up the project.
The second is to process monthly updates. Use this mode when making updates
from a full release.

@author Nicholas Tatonetti, PhD

USAGE
=====

The first time the processor is run must be to download a full release of the
labels. Parsed labels are stored in ./data/spl/rx/[release-file-name]/prescription/.

python3 src/spl_processor.py --full

After that, the update mode can be used to process any available updated labels.

python3 src/spl_processor.py --update

"""

import os
import sys
import csv
import json
import shutil
import hashlib
import argparse
import requests

from tqdm.auto import tqdm
from zipfile import ZipFile
from datetime import datetime
from bs4 import BeautifulSoup

dailymed_spl_resources_url = 'https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm'
dailymed_spl_mapping_resources_url = 'https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-mapping-files.cfm'

section_codes = {
    'AR': '34084-4', # Adverse Reactions
    'BW': '34066-1', # Boxed Warnings
    'WP': '43685-7', # Warnings and Precautions
    'WA': '34071-1', # Warnings
    'PR': '42232-9', # Precautions
    'SP': '43684-0', # Use in Specific Populations
    'OV': '34088-5', # Overdosage
}

def update_spl_status(spl_status, display=False):
    fh = open('./spl.json', 'w')
    fh.write(json.dumps(spl_status, indent=4))
    fh.close()

    if display:
        print(json.dumps(spl_status, indent=4))

def update_process_status(process_status_path, process_status):
    fh = open(process_status_path, 'w')
    fh.write(json.dumps(process_status, indent=4))
    fh.close()

def download_spl_file(url, local_path, proxies = {}):
    # make an HTTP request within a context manager
    with requests.get(url, stream=True, proxies=proxies) as r:
        # check header to get content length, in bytes
        total_length = int(r.headers.get("Content-Length"))
        # implement progress bar via tqdm
        with tqdm.wrapattr(r.raw, "read", total=total_length, desc="")as raw:
            # save the output to a file
            with open(local_path, 'wb') as output:
                shutil.copyfileobj(raw, output)

def download_and_verify(download, archive_info, spl_subdir = 'rx', max_retries=2, proxies={}):
    retry_attemps = 0
    while retry_attemps < max_retries:
        # download
        if not archive_info['downloaded'] == 'yes':
            print(f"Downloading {download['url']}...")
            local_path = os.path.join('data', 'spl', spl_subdir, download['name'])
            if not os.path.exists(local_path):
                download_spl_file(download['url'], local_path, proxies=proxies)

            archive_info['local_path'] = local_path
            archive_info['downloaded'] = 'yes'

        # verify checksum
        if not archive_info['verified'] == 'yes':
            local_path = archive_info['local_path']
            local_md5 = hashlib.md5(open(local_path, 'rb').read()).hexdigest()
            remote_md5 = download['MD5 checksum']
            print(f"Verifying checksum of downloaded file: {local_md5} to expected: {remote_md5}...")
            if not local_md5 == remote_md5:
                print("ERROR: The checksums do not match, there was an error downloading. Will retry up to 2 times.")
                archive_info['downloaded'] = 'no'
                archive_info['local_path'] = ''
                archive_info['verified'] = 'failed'
                retry_attemps += 1
                # remove the file so that it redownloads
                os.unlink(os.path.join('data', 'spl', spl_subdir, download['name']))
            else:
                archive_info['verified'] = 'yes'

        if archive_info['downloaded'] == 'yes' and archive_info['verified'] == 'yes':
            break

def parse_label_xml_from_zip(zip_file, zip_dir_path, label_zip_path, process_status):

    parsed_label = {
        'set_id': '',
        'label_id': '',
        'spl_version': '',
        'sections': dict()
    }

    # zip archive for the label, contains images of the packaging
    # and the text for the label
    with ZipFile(label_zip_path, 'r') as label_zip_obj:

        xml_files = [f for f in label_zip_obj.namelist() if f.endswith('xml')]
        if len(xml_files) != 1:
            raise Exception(f"Label zip archive has an unexpected number of xml files. Expected 1 found {len(xml_files)}.")

        xml_file = xml_files[0]

        xml_file_path = os.path.join(zip_dir_path, '/'.join(os.path.split(zip_file)[:-1]))
        #print(xml_file_path)
        label_zip_obj.extract(xml_file, xml_file_path)

        xml_filename = os.path.join(xml_file_path, xml_file)
        process_status['files'][zip_file]['xml_filename'] = xml_filename

        fh = open(xml_filename)
        xmlsoup = BeautifulSoup(fh.read(), "xml")
        fh.close()

        # parse out set_id and label_id from the xml file
        set_id = xmlsoup.find('setId')['root']
        label_id = xmlsoup.find('id')['root']
        spl_version = xmlsoup.find('versionNumber')['value']

        try:
            title = xmlsoup.title.text.strip()
        except AttributeError:
            title = 'UNDEFINED'

        # Store these identifiers in both places for convenience
        process_status['files'][zip_file]['set_id'] = set_id
        process_status['files'][zip_file]['label_id'] = label_id
        process_status['files'][zip_file]['spl_version'] = spl_version
        process_status['files'][zip_file]['title'] = title
        parsed_label['set_id'] = set_id
        parsed_label['label_id'] = label_id
        parsed_label['spl_version'] = spl_version
        parsed_label['title'] = title
        #update_process_status(process_status_path, process_status)

        #print(title)

        for section_abbrev, section_code in section_codes.items():

            if not section_abbrev in process_status['files'][zip_file]:
                process_status['files'][zip_file]['sections'][section_abbrev] = {
                    'completed': 'no',
                    'error': ''
                }
                #update_process_status(process_status_path, process_status)

            ar_sections = xmlsoup.find_all('code', {'code': section_code})

            if len(ar_sections) == 0:
                process_status['files'][zip_file]['sections'][section_abbrev]['error'] = f'No {section_abbrev} ({section_code}) section found.'

            ar_text = ''
            for ar_section in ar_sections:
                ar_text += ar_section.parent.text.strip()

            #print(section_abbrev)
            #print(ar_text)
            if not ar_text == '':
                parsed_label['sections'][section_abbrev] = ar_text

            process_status['files'][zip_file]['sections'][section_abbrev]['completed'] = 'yes'
            #update_process_status(process_status_path, process_status)

    # finished processing xml file
    label_json_file = os.path.join(zip_dir_path, zip_file.replace('.zip', '.json'))
    process_status['files'][zip_file]['json_filename'] = label_json_file
    #update_process_status(process_status_path, process_status)

    has_data = False
    for section_abbrev in section_codes:
        if section_abbrev in parsed_label['sections']:
            has_data = True
            break

    if has_data:
        fh = open(label_json_file, 'w')
        fh.write(json.dumps(parsed_label, indent=4))
        fh.close()

    # clean up
    os.remove(xml_filename)
    os.remove(label_zip_path)

    process_status['files'][zip_file]['completed'] = 'yes'
    #update_process_status(process_status_path, process_status)

def download_and_process_full_release(soup, spl_status, proxies = {}):

    if spl_status["full_release"]["status"] == "completed":
        raise Exception("ERROR: According to the spl.json file the Full Release is completed. If you are trying to update the labels, use the --update flag.")

    # Full Release: Prescription Labels
    rxtags = soup.find_all("li", {"data-ddfilter": "human prescription labels"})

    available_downloads = list()
    for rxtag in rxtags:
        download_url = rxtag.find('a')['href']
        file_name = os.path.split(download_url)[-1]

        attributes = [['url', download_url], ['name', file_name]]
        for li in rxtag.find_all("li"):
            attributes.append(li.text.split(': '))

        available_downloads.append(dict(attributes))

    print(f"Found {len(available_downloads)} full release download files available.")

    # Step 0. make entries for each download in the json file so we can track
    # their download and processing status and pick up where we left off
    # if needed.
    for download in available_downloads:
        if not download['name'] in spl_status['full_release']['parts']:
            spl_status['full_release']['parts'][download['name']] = download
            spl_status['full_release']['parts'][download['name']]['downloaded'] = 'no'
            spl_status['full_release']['parts'][download['name']]['verified'] = 'no'
            spl_status['full_release']['parts'][download['name']]['parsed'] = 'no'

    update_spl_status(spl_status)

    # Step 1. Download the files and verify their checksums.
    for download in available_downloads:
        download_and_verify(download, spl_status['full_release']['parts'][download['name']], proxies=proxies)
        parsed_labels_path = spl_status['full_release']['parts'][download['name']]['local_path'].strip('.zip')
        spl_status['full_release']['parts'][download['name']]['parsed_labels_path'] = parsed_labels_path
        update_spl_status(spl_status)

    # Step 2. Pre-process files.
    print("Ready to begin pre-processing.")
    for partkey, part in spl_status['full_release']['parts'].items():
        if spl_status['full_release']['parts'][partkey]['parsed'] == 'yes':
            continue

        process_label_archive(part)
        update_spl_status(spl_status)

    # Completed Step 2
    spl_status['full_release']['status'] = 'completed'
    update_spl_status(spl_status)

def process_label_archive(archive_info):

    zip_dir_path = archive_info['parsed_labels_path']
    if not os.path.exists(zip_dir_path):
        os.mkdir(zip_dir_path)

    # Checking for status json file
    process_status = {"files": dict()}
    process_status_path = os.path.join(zip_dir_path, 'process_status.json')
    if os.path.exists(process_status_path):
        fh = open(process_status_path)
        process_status = json.loads(fh.read())
        fh.close()

    with ZipFile(archive_info['local_path'], 'r') as zip_obj:

        # filter out any labels that are not prescription
        zip_files = [f for f in zip_obj.namelist() if f.startswith('prescription') and f.endswith('zip')]
        print(f"  > {archive_info['local_path']} ({len(zip_files)} files.)")

        for zip_i, zip_file in tqdm(enumerate(zip_files), total=len(zip_files)):

            if zip_i % int(len(zip_files) / 10) == 0:
                update_process_status(process_status_path, process_status)

            if not zip_file in process_status['files']:
                process_status['files'][zip_file] = {
                    'completed': 'no',
                    'xml_filename': '',
                    'sections': dict(),
                }
                #update_process_status(process_status_path, process_status)

            if process_status['files'][zip_file]['completed'] != 'yes':

                label_zip_path = os.path.join(zip_dir_path, zip_file)
                if not os.path.exists(label_zip_path):
                    zip_obj.extract(zip_file, zip_dir_path)

                # Parses the different sections of the label and then
                # saves them to a json file of the same name as the xml
                # label.
                parse_label_xml_from_zip(zip_file, zip_dir_path, label_zip_path, process_status)

            # end if completed statment

    # finished processing the zip archive
    update_process_status(process_status_path, process_status)
    archive_info['parsed'] = 'yes'

def download_and_process_updates(soup, spl_status, proxies={}):

    if not spl_status['full_release']['status'] == 'completed':
        raise Exception("ERROR: Can only run update if a full release has previously been completed. To process a full_release, rerun this script using the --full flag.")

    # Get the date that we last updated, could be either the date of the
    # full release or the most recent update. We will make a list of all of
    # the dates for completed downloads and then see what's most recent.

    dates = list()
    for part in spl_status['full_release']['parts'].values():
        dates.append(datetime.strptime(part['Last Modified'], "%b %d, %Y"))

    # for updates, the date is the key
    for update_date in spl_status['updates'].keys():
        dates.append(datetime.strptime(update_date, "%b%Y"))

    most_recent_update_date = max(dates)
    # override the date for dev purposes
    # most_recent_update_date = datetime.strptime("Aug 2022", "%b %Y")

    print(f"Most recent update was on {most_recent_update_date.strftime('%b %Y')}, looking for monthly updates after.")

    update_tags = soup.find_all("li", {"data-ddfilter": "monthly"})

    available_downloads = list()
    for rxtag in update_tags:
        download_url = rxtag.find('a')['href']
        file_name = os.path.split(download_url)[-1]
        update_date = datetime.strptime(file_name.split('.')[0].split('_')[-1], "%b%Y")

        if update_date <= most_recent_update_date:
            continue

        attributes = [['url', download_url], ['name', file_name], ['date', update_date.strftime("%b%Y")]]
        for li in rxtag.find_all("li"):
            attributes.append(li.text.split(': '))

        available_downloads.append(dict(attributes))

    print(f"Found {len(available_downloads)} update(s) available.")

    # Step 1. Download
    for download in available_downloads:
        if not download['date'] in spl_status['updates']:
            spl_status['updates'][download['date']] = {
                'downloaded': 'no',
                'verified': 'no'
            }
        download_and_verify(download, spl_status['updates'][download['date']], proxies=proxies)
        spl_status['updates'][download['date']]['parsed_labels_path'] = spl_status['updates'][download['date']].strip('.zip')
        update_spl_status(spl_status)

    # Step 2. Pre-process files.
    for datekey, update in spl_status['updates'].items():
        if update['parsed'] == 'yes':
            continue

        process_label_archive(update)
        update_spl_status(spl_status)

def download_and_verify_mapping_files(soup, spl_status, proxies = {}):
    maps_dir = os.path.join('data', 'spl', 'maps')
    if not os.path.exists(maps_dir):
        os.mkdir(maps_dir)

    download_list = soup.find("ul", {"class": "download heading"})

    for li in download_list.findChildren("li", recursive=False):

        li_url = li.find_all("a")[0]["href"]
        li_name = os.path.split(li_url)[-1]

        # list of meta data for the download
        li_meta = list()
        li_ul = li.findChildren("ul", recursive=False)[0]
        for li_ul_li in li_ul.find_all("li"):
            li_meta.append( li_ul_li.text.split(': ') )
        li_meta = dict(li_meta)

        li_date = datetime.strptime(li_meta['Last Modified'], "%b %d, %Y").strftime("%Y%m%d")

        if not os.path.exists(os.path.join(maps_dir, li_date)):
            os.mkdir(os.path.join(maps_dir, li_date))

        if not li_name in spl_status['mappings']:
            spl_status['mappings'][li_name] = dict()

        if li_date in spl_status['mappings'][li_name]:
            if spl_status['mappings'][li_name][li_date]['status'] == 'completed':
                continue
        else:
            spl_status['mappings'][li_name][li_date] = {
                'status': 'in_progress',
                'description': '',
                'url': '',
                'downloaded': 'no',
                'verified': 'no',
                'extracted': 'no'
            }

        spl_status['mappings'][li_name][li_date].update( dict(li_meta) )
        spl_status['mappings'][li_name][li_date]['description'] = li.find("h3").text
        spl_status['mappings'][li_name][li_date]['name'] = li_name
        spl_status['mappings'][li_name][li_date]['url'] = li_url

        download_and_verify(spl_status['mappings'][li_name][li_date],
            spl_status['mappings'][li_name][li_date],
            spl_subdir=os.path.join('maps', li_date),
            proxies=proxies)

        # extract the data file out and gzip it
        with ZipFile(spl_status['mappings'][li_name][li_date]['local_path']) as zip_obj:
            txt_fn = li_name.replace('.zip', '.txt')
            if not txt_fn in zip_obj.namelist():
                raise Exception(f"ERROR: Did not find expected file {txt_fn} in the zip archive: {spl_status['mappings'][li_name][li_date]['local_path']}.")

            zip_dir_path = os.path.dirname(spl_status['mappings'][li_name][li_date]['local_path'])
            zip_obj.extract(txt_fn, zip_dir_path)
            spl_status['mappings'][li_name][li_date]['extracted'] = 'yes'
            spl_status['mappings'][li_name][li_date]['extracted_path'] = spl_status['mappings'][li_name][li_date]['local_path'].replace('.zip', '.txt')

        if spl_status['mappings'][li_name][li_date]['downloaded'] == 'yes' and \
            spl_status['mappings'][li_name][li_date]['verified'] == 'yes' and \
            spl_status['mappings'][li_name][li_date]['extracted'] == 'yes':
            spl_status['mappings'][li_name][li_date]['status'] = 'completed'

    update_spl_status(spl_status)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', '--full-release', help='Process from the full release files.', action='store_true', default=False)
    parser.add_argument('--update', help="Process any available update files.", action='store_true', default=True)
    parser.add_argument('--http-proxy', help="Define a proxy server to use for the requests library.", default=None)
    parser.add_argument('--local-resources', help="Can override URL with a local file path to the file. Not recommended.", default=None)
    parser.add_argument('--local-mappings', help="Can override URL with a local file path to the file. Not recommended.", default=None)

    # TODO: Implement for other label types as we have models for them. Currently only available for prescriptions.
    # parser.add_argument('--type', help="Which types of labels to process. Possible values include rx (Prescription)[Default] or otc (Over-the-Counter).", type=str, default="rx")
    args = parser.parse_args()

    if args.full:
        args.update = False

    if args.update and not os.path.exists('./spl.json'):
        raise Exception("First run must be to get a full release. Re-run with the --full flag.")

    proxies = {}
    if not args.http_proxy is None:
        proxies['http'] = args.http_proxy
        proxies['https'] = args.http_proxy
        print(f"Will use proxy: {args.http_proxy}")

    if not args.local_resources is None:
        content = open(args.local_resources).read()
    else:
        page = requests.get(dailymed_spl_resources_url, proxies=proxies)
        content = page.content

    soup = BeautifulSoup(content, "html.parser")

    spl_status = {"full_release": {"status": "in_progress", "parts": dict()}, "updates": dict(), "mappings": dict(), "last_updated": "20010101"}
    if os.path.exists('./spl.json'):
        splfh = open('./spl.json')
        spl_status = json.loads(splfh.read())
        splfh.close()

    if args.update:
        download_and_process_updates(soup, spl_status, proxies=proxies)
    elif args.full:
        download_and_process_full_release(soup, spl_status, proxies=proxies)
    else:
        raise Exception("Either --full or --update flag must be provided.")

    # Get the latest mapping files
    if not args.local_mappings is None:
        content = open(args.local_mappings).read()
    else:
        page = requests.get(dailymed_spl_mapping_resources_url, proxies=proxies)
        content = page.content

    soup = BeautifulSoup(content, "html.parser")

    download_and_verify_mapping_files(soup, spl_status, proxies=proxies)

    spl_status["last_updated"] = datetime.now().strftime("%Y%d%m")
    update_spl_status(spl_status)

if __name__ == '__main__':
    main()
