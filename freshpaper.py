import os
import re
import sys
import click
import json
import logging
from random import choice
from datetime import datetime
from subprocess import check_call, CalledProcessError
# from PIL import Image

try:
    # for python3
    from urllib.request import urlopen, urlretrieve, HTTPError, URLError
except ImportError:
    # for python2
    from urllib import urlretrieve
    from urllib2 import urlopen, HTTPError, URLError

if sys.platform.startswith("win32"):
    import win32api
    import win32con
    import win32gui

logging.basicConfig(level=logging.INFO, format="%(message)s")

log = logging.getLogger(__name__)

# TODO:
# handle 404
class FreshPaper:
    def __init__(self):
        self.wallpaper_directory = self.get_wallpaper_directory()

    @staticmethod
    def get_wallpaper_directory():
        """ check if `default` wallpaper download directory exists or not, create if doesn't exist """
        pictures_dir = ""
        wall_dir_name = "freshpaper"
        os.path.join(os.sep, os.path.expanduser("~"), "a", "freshpaper")
        if sys.platform.startswith("win32"):
            pictures_dir = "Pictures"
        elif sys.platform.startswith("darwin"):
            pictures_dir = "Pictures"
        elif sys.platform.startswith("linux"):
            pictures_dir = "Pictures"
        wall_dir = os.path.join(
            os.sep, os.path.expanduser("~"), pictures_dir, wall_dir_name
        )

        if not os.path.isdir(wall_dir):
            log.error("wallpaper directory does not exist.")
            os.makedirs(wall_dir)
            log.info("created wallpaper directory at: {}".format(wall_dir))

        return wall_dir

    def get_random_saved_wallpaper(self):
        """ returns random saved wallpaper's path """

        files = os.listdir(self.wallpaper_directory)
        if files:
            log.info("\nRandomly picking from saved wallpapers.")
            image_name = choice(files)
            image_path = os.path.join(os.sep, self.wallpaper_directory, image_name)
            return image_path
        else:
            log.error("There is no wallpaper available offline.")
            sys.exit(1)

    @staticmethod
    def convert_camel_case(text, sep):
        return re.sub("([a-z])([A-Z])", r"\1{}\2".format(sep), text)

    @staticmethod
    def get_request(url, *args, **kwargs):
        try:
            return urlopen(url, *args, **kwargs).read().decode("utf-8")
        except URLError:
            log.error("Something went wrong..\nMaybe Internet is not working...")
            raise ConnectionError

    def get_wallpaper_urls(self):
        raise NotImplemented

    def download_wallpaper(self):
        image_name, image_url_sd, image_url_hd = self.get_wallpaper_urls()
        image_name = re.sub(r'[?*/:<>"\|]', ' ', image_name)

        date_time = datetime.now().strftime("%d_%m_%Y")
        image_file_name = "{image_name}_{date_stamp}.{extention}".format(
            image_name=image_name.replace(" ", "_").lower(),
            date_stamp=date_time,
            extention="jpg",
        )

        image_path = os.path.join(os.sep, self.wallpaper_directory, image_file_name)
        log.debug("download_dir: {}".format(self.wallpaper_directory))
        log.info("image_file_name: {}".format(image_file_name))
        log.info("image_path: {}".format(image_path))

        if os.path.isfile(image_path):
            log.info("No new wallpaper yet..updating to latest one.\n")
            return image_path

        try:
            log.info("Downloading HD image..")
            urlretrieve(image_url_hd, filename=image_path)
        except HTTPError:
            log.info("Downloading SD image...")
            urlretrieve(image_url_sd, filename=image_path)
        return image_path

    @staticmethod
    def set_wallpaper(image_path):
        if image_path is None:
            return
        """ Given a path to an image, set it as the wallpaper """
        if not os.path.exists(image_path):
            log.error("Image does not exist.")
            sys.exit(1)

        log.info("Updating wallpaper..")
        log.info(
            "Name of wallpaper: {}".format(
                re.sub(
                    "([a-z])([A-Z])", r"\1 \2", image_path.split("/")[-1].split(".")[0]
                )
            )
        )

        if sys.platform.startswith("win32"):

            # bmp_image = Image.open(image_path)
            # bmp_img_path = os.path.splitext(image_path)[0] + ".bmp"
            # bmp_image.save(bmp_img_path, "BMP")
            bmp_img_path = image_path
            key = win32api.RegOpenKeyEx(
                win32con.HKEY_CURRENT_USER,
                "Control Panel\\Desktop",
                0,
                win32con.KEY_SET_VALUE,
            )
            win32api.RegSetValueEx(key, "WallpaperStyle", 0, win32con.REG_SZ, "10")
            win32api.RegSetValueEx(key, "TileWallpaper", 0, win32con.REG_SZ, "0")
            win32gui.SystemParametersInfo(
                win32con.SPI_SETDESKWALLPAPER, bmp_img_path, 1 + 2
            )
            os.remove(bmp_img_path)
        elif sys.platform.startswith("darwin"):
            try:
                command = """
                    osascript -e 'tell application "System Events"
                        set desktopCount to count of desktops
                        repeat with desktopNumber from 1 to desktopCount
                            tell desktop desktopNumber
                                set picture to "{image_path}"
                            end tell
                        end repeat
                    end tell'
                    """.format(
                    image_path=image_path
                )

                check_call([command], shell=True)
            except (CalledProcessError, FileNotFoundError):
                log.error("Setting wallpaper failed.")
                sys.exit(1)
        elif sys.platform.startswith("linux"):
            check_call(
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.background",
                    "picture-uri",
                    "file://{}".format(image_path),
                ]
            )

        log.info("Wallpaper successfully updated. :)")

    def refresh_wallpaper(self):
        try:
            image_path = self.download_wallpaper()
            FreshPaper.set_wallpaper(image_path)
        except ConnectionError:
            image_path = self.get_random_saved_wallpaper()
            FreshPaper.set_wallpaper(image_path)
        except Exception as e:
            log.error(e)


class Bing(FreshPaper):
    name = "bing"

    def get_wallpaper_urls(self):
        """
        returns wallpaper url
        :return: returns wallpaper image name, sd_url and hd_url
        """

        url = "http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=EN-US"

        image_data = json.loads(self.get_request(url))
        image0 = image_data["images"][0]

        image_url_sd = "http://www.bing.com" + image0["url"]

        image_name = re.search(r"OHR\.(.*?)_", image_url_sd).group(1)
        image_name = self.convert_camel_case(image_name, " ")

        # image_url_hd = "http://www.bing.com/hpwp/" + image0["hsh"]
        image_url_hd = "http://www.bing.com" + image0["urlbase"] + "_UHD.jpg"

        return image_name, image_url_sd, image_url_hd


class Nasa(FreshPaper):
    name = "nasa"

    def get_wallpaper_urls(self):
        """
        returns wallpaper url
        :return: returns wallpaper image name, sd_url and hd_url
        """

        url = "https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"

        image_data = json.loads(self.get_request(url))

        if image_data.get("media_type") != "image":
            raise ValueError("No NASA image of the day available for today.")

        image_url_sd = image_data.get("url")

        # image_name = url.split("/")[-1] #.split("_")[0]
        # image_name = self.convert_camel_case(image_name, " ")
        # image_name = re.sub(r'[?*/:<>"\|]', ' ', image_name)
        image_name = image_data['title']

        image_url_hd = image_data.get("hdurl")

        return image_name, image_url_sd, image_url_hd


class NatGeo(FreshPaper):
    name = "nat_geo"

    def get_wallpaper_urls(self):
        """
        returns wallpaper url
        :return: returns wallpaper image name, sd_url and hd_url
        """

        url = "https://www.nationalgeographic.com/photography/photo-of-the-day/"

        html = self.get_request(url)
        url_regex = r'twitter:image:src"\s+content="([^">]*)"'
        image_url_sd = image_url_hd = re.findall(url_regex, html)[0]
        log.info('image_url_sd ' + image_url_sd)

        if not image_url_sd:
            log.info("No National Geographic image of the day available.\n")
            return None

        image_name_regex = r'twitter:title"\s+content="([^">]*)"'
        image_name = re.findall(image_name_regex, html)[0]
        log.info('image name ' + image_name)

        if not image_name:
            image_name = "nat_geo"

        return image_name, image_url_sd, image_url_hd


class UnsplashRandom(FreshPaper):
    name = "unsplash_random"

    def get_wallpaper_urls(self):
        """
        returns wallpaper url
        :return: returns wallpaper image name, sd_url and hd_url
        """

        url = "https://source.unsplash.com/random/3840x2160"

        image_name = "unsplash_random"

        image_url_sd = image_url_hd = url

        return image_name, image_url_sd, image_url_hd


freshpaper_sources = {
    freshpaper_source.name: freshpaper_source
    for freshpaper_source in FreshPaper.__subclasses__()
}


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.pass_context
@click.option(
    "--source",
    default="bing",
    type=click.Choice(freshpaper_sources.keys()),
    help="Source for setting the wallpaper.",
)
def main(ctx, source):
    if ctx.invoked_subcommand is None:
        source_class = freshpaper_sources.get(source)
        source = source_class()
        source.refresh_wallpaper()


if __name__ == "__main__":
    main()
