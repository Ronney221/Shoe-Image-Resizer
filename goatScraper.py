import os
import time
import requests
import zipfile
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def setup_driver():
    # Set up Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # If ChromeDriver is not in your PATH, specify its location using executable_path
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def scroll_page(driver, pause_time=3):
    # Scroll to the bottom of the page to ensure all dynamic content loads
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def get_image_urls(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    img_tags = soup.find_all("img")
    img_urls = set()
    
    # Loop through each image tag and extract the URL
    for img in img_tags:
        src = img.get("src")
        if src and src.startswith("http"):
            img_urls.add(src)
    return list(img_urls)

def download_images(img_urls, download_folder="images"):
    os.makedirs(download_folder, exist_ok=True)
    downloaded_files = []
    for idx, img_url in enumerate(img_urls):
        try:
            print(f"Downloading image {idx + 1}/{len(img_urls)}: {img_url}")
            response = requests.get(img_url, stream=True, timeout=10)
            response.raise_for_status()  # Raise an error on bad status
            # Determine the file extension; default to .jpg if none found
            ext = os.path.splitext(img_url)[1].split("?")[0]
            if not ext or len(ext) > 5:  # basic check to avoid very long extensions
                ext = ".jpg"
            filename = os.path.join(download_folder, f"image_{idx}{ext}")
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            downloaded_files.append(filename)
        except Exception as e:
            print(f"Error downloading {img_url}: {e}")
    return downloaded_files

def zip_images(folder="images", zip_name="images.zip"):
    with zipfile.ZipFile(zip_name, "w") as zipf:
        for root, _, files in os.walk(folder):
            for file in files:
                filepath = os.path.join(root, file)
                # Use arcname to store files without the folder structure if desired
                zipf.write(filepath, arcname=file)
    print(f"Images zipped into {zip_name}")

def main():
    url = "https://www.goat.com/collections/just-dropped"
    
    # Set up the Selenium driver
    driver = setup_driver()
    print(f"Opening {url}")
    driver.get(url)
    
    # Allow time for the page to load initial content
    time.sleep(5)
    
    # Scroll to the bottom to trigger lazy-loading of images
    scroll_page(driver, pause_time=3)
    
    # Get the rendered page source
    page_source = driver.page_source
    driver.quit()
    
    # Extract image URLs from the page source
    img_urls = get_image_urls(page_source)
    print(f"Found {len(img_urls)} images.")
    
    # Download images locally
    downloaded_files = download_images(img_urls)
    if downloaded_files:
        # Zip the downloaded images
        zip_images()
    else:
        print("No images were downloaded.")

if __name__ == "__main__":
    main()
