from freshdesk.api import API
from dateutil.tz import tzutc
import datetime
import time
import json
import os
import filecmp
import requests
import json

class MyFreshdesk():
    def __init__(self, domain, api_key):
        self.domain = domain
        self.api_key = api_key
        self.json_raw_file = "data/freshdesk_raw_data.json"
        self.old_articles_dir = "data/old"
        self.new_articles_dir = "data/new"
        self.delay_time = 0.1
    
    def _retrieve_all_published_articles(self):        
        a = API(self.domain, self.api_key)
        categories = a.solutions.categories.list_categories()
        all_articles = []

        for category in categories:
            category_id = category.id
            folders = a.solutions.folders.list_from_category(category_id)

            for folder in folders:
                folder_id = folder.id
                articles = a.solutions.articles.list_from_folder(folder_id)

                for article in articles:
                    article_id = article.id
                    article = a.solutions.articles.get_article(article_id)
                    if article.status == "published":
                        one_article = self._convert_articles_to_dictionary(article)
                        all_articles.append(one_article)
                        time.sleep(self.delay_time)

            print(f"Retrieved articles from category: {category.name}")
        
        self._store_raw_articles_in_json_file(all_articles)
        return all_articles

    def retrieve_articles_and_store_as_html(self, is_test=False):
        if is_test:
            # test execution - load from existing json file for time saving
            all_articles = self._retrieve_raw_articles_from_json_file()
        else:
            # real execution - take around 5 minutes to retrieve all articles
            all_articles = self._retrieve_all_published_articles()

        # clean up old articles in old articles directory
        for file in os.listdir(self.old_articles_dir):
            os.remove(f"{self.old_articles_dir}/{file}")
        
        for article in all_articles:
            # get article's id and description
            # store as html file with name is id and content is description
            article_id = article["id"]
            article_description = article["description"]
            
            with open(f"{self.old_articles_dir}/{article_id}.html", 'w', encoding='utf-8') as f:
                f.write(article_description)
        
        return all_articles
    
    def get_all_updated_article_ids(self):
        common_files = set(os.listdir(self.old_articles_dir)).intersection(set(os.listdir(self.new_articles_dir)))

        # Initialize list to store IDs of changed articles
        changed_articles = []

        # Compare each common file
        for file in common_files:
            if not filecmp.cmp(os.path.join(self.old_articles_dir, file), os.path.join(self.new_articles_dir, file)):
                # If file contents are not the same, extract the article ID and add it to the list
                article_id = file.split('.')[0]  # Assumes file name format is "article_{id}.html"
                changed_articles.append(article_id)

        return changed_articles
    
    def revert_articles_with_old_content(self, article_ids):
        self.update_articles(self.old_articles_dir, article_ids)

    def update_articles_with_new_content(self, article_ids):
        self.update_articles(self.new_articles_dir, article_ids)

    def update_articles(self, dir, article_ids):
        for article_id in article_ids:
            # read new content from file
            with open(f"{dir}/{article_id}.html", 'r', encoding='utf-8') as f:
                new_content = f.read()

            # Your Freshdesk domain and API key
            domain = self.domain
            api_key = self.api_key

            # The URL of the article
            url = f'https://{domain}/api/v2/solutions/articles/{article_id}'

            # The headers for the request
            headers = {
                'Content-Type': 'application/json',
            }

            # The data for the request
            data = {
                'description': new_content,
                'status': 2,  # 2 means 'published'
            }

            # Make the PUT request
            response = requests.put(url, auth=(api_key, 'X'), headers=headers, data=json.dumps(data))

            # Check the response
            if response.status_code == 200:
                print(f'Article {article_id} updated and published successfully')
            else:
                print(f'Failed to update and publish article: {response.content}')

    def _convert_articles_to_dictionary(self, article):
        return {
            "id": article.id,
            "folder_id": article.folder_id,
            "category_id": article.category_id,
            "status": article.status,
            "title": article.title,
            "description": article.description,
            "hits": article.hits,
            "thumbs_up": article.thumbs_up,
            "thumbs_down": article.thumbs_down,
            "tags": article.tags,
            "updated_at": article.updated_at
        }
    
    def _store_raw_articles_in_json_file(self, all_articles):
        with open(self.json_raw_file, 'w', encoding='utf-8') as f:
            f.write(str(all_articles))

    def _retrieve_raw_articles_from_json_file(self):
        with open(self.json_raw_file, 'r', encoding='utf-8') as f:
            return eval(f.read())