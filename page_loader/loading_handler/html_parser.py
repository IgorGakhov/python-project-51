import os
from urllib.parse import urlparse, urljoin
from typing import Final, List, Dict, Tuple

import requests
from bs4 import BeautifulSoup

from page_loader.loading_handler.file_system_guide import \
    parse_url, get_dir_name, HTML_EXT
from page_loader.logger import logger, \
    START_PARSING, END_PARSING, START_SEARCHING, END_SEARCHING, \
    START_SAVING, END_SAVING, START_GET_RESOURCE, END_GET_RESOURCE, \
    START_SAVE_RESOURCE, END_SAVE_RESOURCE


TAGS_LINK_ATTRIBUTES: Final[Dict] = {
    'img': 'src',
    'link': 'href',
    'script': 'src',
}
DOMAIN_ADDRESS: Final[str] = '{}://{}'


def parse_page(url: str, dir_path: str) -> str:
    '''
    Description:
    ---
        Gets the content of a web page, processes links,
        downloads local resources, and returns the rendered HTML.

    Parameters:
    ---
        - url (str): Page being downloaded.
        - dir_path (str): Full path of the directory in the file system.

    Return:
    ---
        html (str): Processed HTML page with replaced links.
    '''
    logger.debug(START_PARSING)

    page = requests.get(url)
    html, resources = search_resources(page.text, url)

    save_resources(resources, dir_path)

    logger.debug(END_PARSING)

    return html


def search_resources(html: str, page_url: str) -> Tuple[str, List[Dict]]:
    '''Replaces resource links with their paths in the file system,
    returns the processed html and download links of these resources.'''
    logger.debug(START_SEARCHING)

    dir_name = get_dir_name(page_url)

    soup = BeautifulSoup(html, 'html.parser')

    resources = []
    for resource_tag in TAGS_LINK_ATTRIBUTES.keys():
        for tag in soup.find_all(resource_tag):
            link_attr = TAGS_LINK_ATTRIBUTES[tag.name]

            link = get_full_link(tag[link_attr], page_url)
            if is_local_link(link, page_url):

                resource_name = create_resource_name(link)
                tag[link_attr] = os.path.join(dir_name, resource_name)

                resource = {
                    'link': link,
                    'name': resource_name
                }
                resources.append(resource)

    html = soup.prettify()

    logger.debug(END_SEARCHING)

    return html, resources


def get_full_link(link: str, page_url: str) -> str:
    '''Returns the full URL of the link.'''
    url_domain_address = DOMAIN_ADDRESS.format(
        urlparse(page_url).scheme, urlparse(page_url).netloc
    )

    rsc_netloc = urlparse(link).netloc
    if not rsc_netloc:
        link = urljoin(url_domain_address, link)

    return link


def is_local_link(link: str, page_url: str) -> bool:
    '''Checks if the resource is local to the downloaded page.'''
    rsc_netloc = urlparse(link).netloc
    url_netloc = urlparse(page_url).netloc

    return rsc_netloc == url_netloc


def create_resource_name(link: str) -> str:
    '''Formats a resource link and returns a name for the storage file
    (without the name of the storage directory).'''
    parsed_resource_link = parse_url(link)
    netloc = parsed_resource_link['netloc']
    path = parsed_resource_link['path']
    ext = parsed_resource_link['ext']
    ext = ext if ext else HTML_EXT

    resource_name = f'{netloc}-{path}.{ext}'

    return resource_name


def save_resources(resources: List, dir_path: str) -> None:
    '''Iterates through the passed list of resources,
    saves them locally at the given location.'''
    logger.debug(START_SAVING)

    for resource in resources:

        logger.debug(START_GET_RESOURCE.format(resource['link']))

        content = requests.get(resource['link']).content

        logger.debug(END_GET_RESOURCE.format(resource['link']))

        resource_path = os.path.join(dir_path, resource['name'])

        logger.debug(
            START_SAVE_RESOURCE.format(resource['link'], resource_path)
        )

        with open(resource_path, 'wb') as file:
            file.write(content)

        logger.info(END_SAVE_RESOURCE.format(resource['link']))

    logger.debug(END_SAVING)
