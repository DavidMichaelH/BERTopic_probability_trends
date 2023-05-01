import requests
import pandas as pd
import time
import xml.etree.ElementTree as ET
import os
from datetime import datetime, timedelta
import pytz

 


def date_range(start_date, end_date, delta=timedelta(days=30)):
    current_date = start_date
    while current_date < end_date:
        next_date = current_date + delta
        yield current_date, min(next_date, end_date)
        current_date = next_date


def collect_arxiv_metadata(num_papers, category, start_date=None, end_date=None):
    base_url = 'http://export.arxiv.org/api/query?'
    papers = []
    unique_arxiv_ids = set()

    start_index = 0
    batch_size = 2000

    while len(papers) < num_papers:
        query = f'cat:{category}'
        url = f'{base_url}search_query={query}&start={start_index}&max_results={batch_size}&sortBy=submittedDate&sortOrder=descending'
        if start_date is not None and end_date is not None:
            url += f'&date_from={start_date.isoformat()}&date_until={end_date.isoformat()}'
        response = requests.get(url)
        root = ET.fromstring(response.content)

        fetched_papers = []
        earliest_date = None
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            arxiv_id = entry.find('{http://www.w3.org/2005/Atom}id').text.split('/')[-1]

            if arxiv_id not in unique_arxiv_ids:
                unique_arxiv_ids.add(arxiv_id)
                date = entry.find('{http://www.w3.org/2005/Atom}published').text
                date = date.replace("Z", "+00:00")

                title = entry.find('{http://www.w3.org/2005/Atom}title').text.replace('\n', ' ').strip()
                authors = ', '.join([author.find('{http://www.w3.org/2005/Atom}name').text for author in entry.findall('{http://www.w3.org/2005/Atom}author')])
                abstract = entry.find('{http://www.w3.org/2005/Atom}summary').text.replace('\n', ' ').strip()

                metadata = {
                    'title': title,
                    'authors': authors,
                    'date': date,
                    'abstract': abstract,
                    'arxiv_id': arxiv_id
                }
                fetched_papers.append(metadata)

                # Track the earliest date
                paper_date = datetime.fromisoformat(date)
                if earliest_date is None or paper_date < earliest_date:
                    earliest_date = paper_date

        if fetched_papers:
            papers.extend(fetched_papers)
            start_index += batch_size
        else:
            break

        # Stop fetching if the earliest paper in the batch is older than the start_date
        if start_date is not None and earliest_date < start_date:
            break

        time.sleep(6)  # To respect arxiv API rate limits (1 request every 3 seconds)
        print(f'Fetched {len(papers)} papers')

    return papers[:num_papers]




def save_metadata_to_csv(metadata_list, output_filename):
    df = pd.DataFrame(metadata_list)
    file_exists = os.path.isfile(output_filename)
    
    if file_exists:
        counter = 1
        filename_without_extension, extension = os.path.splitext(output_filename)
        
        while file_exists:
            new_filename = f"{filename_without_extension}_{counter}{extension}"
            file_exists = os.path.isfile(new_filename)
            counter += 1
        
        output_filename = new_filename
        
    df.to_csv(output_filename, index=False)
    return output_filename
 
 
if __name__ == '__main__':
    category = 'math.PR'  # Probability category
    #category = 'stat.ML'
    num_papers = 20000  # Increase the number of papers fetched
    output_filename = 'arxiv_probability_metadata_22_23.csv'

    utc = pytz.UTC
    start_date = datetime(2017, 1, 1, tzinfo=utc)  # Specify the start date with UTC timezone
    end_date = datetime(2023, 4, 6, tzinfo=utc)  # Specify the end date with UTC timezone

    metadata_list = collect_arxiv_metadata(num_papers, category, start_date=start_date, end_date=end_date)
    #metadata_list = collect_arxiv_metadata_segmented(num_papers, category, start_date=start_date, end_date=end_date)
    saved_filename = save_metadata_to_csv(metadata_list, output_filename)
    print(f'Metadata for papers between {start_date} and {end_date} saved to {saved_filename}')


    