# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------------------
import os
import re
import json
import gc
import mechanize
import bs4
import cookielib
import logging
import platform

from time import sleep


# User defined vars
#----------------------------------------------------------------------------------------
# Netflix email and password
username = ''
password = ''

# where to store collected shows
sourceDir = ''

# globals
#----------------------------------------------------------------------------------------

netflixLogin = 'https://www.netflix.com/Login?locale=en-US'
netflixHome  = 'http://www.netflix.com/WiHome'
httpBase     = 'http://www.netflix.com'
mediaHttp    = '%s/WiMovie' % httpBase
seasonHttp   = mediaHttp + '/%(titleid)s?actionMethod=seasonDetails&seasonId=' \
                           '%(seasonID)s&seasonKind=ELECTRONIC'
showAPI      = 'http://api-global.netflix.com/desktop/odp/episodes?video='     \
               '%(titleid)s&country=US&languages=en-US&routing=redirect'
movieAPI     = "http://www.netflix.com/api/shakti/%(identifier)s/bob?titleid=" \
               "%(titleid)s&trackid=%(trackId)s"
videoURL     = "http://www.netflix.com/WiPlayer?movieid=%(episodeId)s&trkid="  \
               "%(trackId)s"

resourcePath = os.path.normpath(os.path.join(os.path.split(__file__)[:-1][0], 'resources'))

# enumerations
#----------------------------------------------------------------------------------------

kCategoryName = 0
kGenre        = 1
kCategoryURL  = 1
kGenreURL     = 2

# objects
#----------------------------------------------------------------------------------------



class Categories(object): pass
class Genres(object): pass

class NetflixCollector(object):

    ID_REGEX    = re.compile(r"BUILD_IDENTIFIER[\'\"]:[\'\"]([a-zA-Z0-9]*)")
    CLEAN_REGEX = re.compile(r"[^a-zA-Z0-9'&! _-]")
    RETRIES     = 3

    LOGGER      = logging.getLogger('NetflixCrawler')
    LOGGER.setLevel(logging.INFO)
    CH = logging.StreamHandler()
    CH.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s] : %(message)s')
    CH.setFormatter(formatter)
    LOGGER.addHandler(CH)

    def __init__(self):
        self.browser    = mechanize.Browser()
        self.cj         = cookielib.LWPCookieJar()
        self.categories = {}
        self.mediaInfo  = {}
        self.identifier = ''
        self.sourceDir  = sourceDir if sourceDir else self.defaultSourceDir()

    # Main App crawler
    def collectNetflix(self):
        self.LOGGER.info("Starting crawl")
        self.login()
        homePage = self.readURL(netflixHome)
        self.getCategories(homePage)
        self.collectIdentifier()
        self.browseGenres()
        self.collectMedia()

    def browserOptions(self):
        self.LOGGER.info("Setting Browser")
        self.browser.set_cookiejar(self.cj)
        self.browser.set_handle_equiv(True)
        self.browser.set_handle_redirect(True)
        self.browser.set_handle_referer(True)
        self.browser.set_handle_robots(False)
        self.browser.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
        self.browser.addheaders = [('user-agent',
                                    ' Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.3) '
                                    ' Gecko/20100423 Ubuntu/10.04 (lucid) Firefox/3.6.3'),
                                   ('accept',
                                    'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')]
        self.browser.addheaders.append(("Accept-Language", "en-us,en"))

    # Login to netflix
    def login(self):
        self.LOGGER.info("Loggin in")
        self.browserOptions()
        self.browser.open(netflixLogin)
        self.browser.form = list(self.browser.forms())[0]
        if self.browser.form:
            self.browser['email']    = username
            self.browser['password'] = password
            self.browser.submit()

    #------------------------------------------------------------------------------------
    # html parsing methods
    #------------------------------------------------------------------------------------

    def collectIdentifier(self):
        self.LOGGER.info("Collecting identifier")
        key     = self.categories.keys()[0]
        soup    = self.readURL(self.categories[key].href)
        scripts = "".join([str(x) for x in soup.findAll('script')])
        id      = re.search(self.ID_REGEX, scripts)
        if id:
            self.identifier = id.group(1)
            self.LOGGER.info("Collected identifier: %s" % self.identifier)
        else:
            self.LOGGER.critical("Identifier not found. Exiting.")
            raise Exception("Unable to get indentifier. Cannot crawl netflix without it. TRY AGAIN!")

    # collect browse categories
    def getCategories(self, soup):
        self.LOGGER.info("Collecting Categories")
        for flixTitle in soup.findAll("li", {"id": "nav-watchinstantly"}):
            for browse in flixTitle.findAll('li'):
                sectionTitle = browse.find('a')
                if sectionTitle and self.notSubNav(browse):
                    self.LOGGER.info("Collected: %s %s" % (sectionTitle.string,
                                                            sectionTitle['href']))
                    self.categories[sectionTitle.string] = Categories()
                    self.categories[sectionTitle.string].href = sectionTitle['href']

    def browseGenres(self):
        self.LOGGER.info("Collecting Genres")
        for name, category in self.categories.iteritems():
            category.genres = {}
            soup     = self.readURL(category.href)
            try:
                genreDiv = soup.find("div", {"id": "subGenres_trigger"})
                for genre in genreDiv.findAll('li'):
                    sectionTitle = genre.find('a')
                    if sectionTitle:
                        category.genres[sectionTitle.string] = Genres()
                        category.genres[sectionTitle.string].href = sectionTitle['href']
                        self.LOGGER.info("Adding to %s: %s" % (name, sectionTitle.string))
            except AttributeError, e:
                self.LOGGER.error("Unable to collect a genre for: %(name)s \n %(e)s" % locals())
                continue

    def collectMedia(self):
        self.LOGGER.info("Collecting Media")
        for categoryTitle, category in self.categories.iteritems():
            for genreTitle, genreMedia in category.genres.iteritems():
                saveDir  = self.createDir(categoryTitle, genreTitle)
                soup     = self.readURL(genreMedia.href)
                mediaDiv = soup.findAll("div", {"class": "lockup"})
                for media in mediaDiv:
                    try:
                        self.mediaInfo['locator']    = "%(categoryTitle)s - %(genreTitle)s" % locals()
                        self.mediaInfo['titleid']    = media['data-titleid']
                        self.mediaInfo['trackId']    = media['data-trackid']
                        self.mediaInfo['identifier'] = self.identifier
                        res = self.openURL(movieAPI % self.mediaInfo)
                        mediaInfoURL = '/'.join([mediaHttp, self.mediaInfo['titleid']])
                        mediaThumb   = media.find("img", {"class", "boxart"})['src']
                        mediaURL     = media.find("a", {"class", "playHover"})['href']
                        self.mediaInfo.update(json.loads(res.read()))
                        self.mediaInfo['title'] = self.cleanText(self.mediaInfo['title'])
                        self.mediaInfo['thumb'] = str(mediaThumb)
                        self.mediaInfo['url']   = str(mediaURL)
                        self.mediaInfo['genreDir'] = saveDir
                        saveFile = os.path.join(saveDir, self.mediaInfo['title'])
                        if os.path.exists(saveFile) or os.path.isfile(saveFile + '.avi'):
                            continue
                        self.collectMediaInfo(mediaInfoURL, saveDir)
                        del self.mediaInfo
                        self.mediaInfo = {}
                        gc.collect()
                    except Exception, e:
                        self.LOGGER.error("%s" % e)
                        continue


    def collectMediaInfo(self, url, saveDir):
        self.LOGGER.info("Collecting: %s %s" % (self.mediaInfo['locator'], self.mediaInfo['title']))
        if self.mediaInfo['isMovie'] and ('TV' not in saveDir):
            self.movie()
        if self.mediaInfo['isShow'] and ('TV' in saveDir):
            self.tvShow()

    def movie(self):
        saveFile  = os.path.join(self.mediaInfo['genreDir'], self.mediaInfo['title'])
        self.createDir(path=self.mediaInfo['genreDir'])
        self.createNFO(saveFile, 'movie')
        self.saveMedia('', saveFile, 'avi')

    def tvShow(self):
        saveBase = os.path.join(self.mediaInfo['genreDir'], self.mediaInfo['title'])
        res = self.openURL(showAPI % self.mediaInfo)
        mediaDict = json.loads(res.read())
        for season in mediaDict['episodes']:
            for episode in season:
                try:
                    self.mediaInfo['episodeTitle'] = self.cleanText(episode['title'])
                    self.mediaInfo['season']       = episode['season']
                    self.mediaInfo['synopsis']     = episode['synopsis']
                    self.mediaInfo['episodeNum']   = episode['episode']
                    self.mediaInfo['episodeId']    = episode['episodeId']
                    self.mediaInfo['episodeUrl']   = videoURL % self.mediaInfo
                    try:
                        self.mediaInfo['thumb'] = episode['stills'][1]['url']
                    except IndexError:
                        self.mediaInfo['thumb'] = episode['stills'][0]['url']
                    mediaName = "%s_s%02d_e%02d" % (self.mediaInfo['episodeTitle'],
                                                    int(self.mediaInfo['season']),
                                                    int(self.mediaInfo['episodeNum']))
                    seasonDir = "Season %(season)s" % self.mediaInfo
                    savePath = os.path.join(saveBase, seasonDir)
                    saveFile = os.path.join(savePath, mediaName)
                    self.createDir(path=savePath)
                    self.createNFO(saveFile, 'show')
                    self.saveMedia('', saveFile, 'avi')
                except Exception:
                    pass

    #------------------------------------------------------------------------------------
    # Utilities
    #------------------------------------------------------------------------------------
    def createNFO(self, savePath, mediaType):
        nfoFile = 'showNFO.xml' if mediaType == 'show' else 'movieNFO.xml'
        NFO = os.path.join(resourcePath, 'templates', nfoFile)
        with open(NFO, 'rU') as f:
            NFO = str(f.read())
        NFO %= self.mediaInfo
        self.saveMedia(NFO, savePath, 'nfo')

    def openURL(self, url):
        try:
            return self.browser.open(url)
        except Exception:
            print 'sleeping for 8 seconds'
            self.RETRIES -= 1
            if self.RETRIES <= 0:
                self.RETRIES = 3
                return False
            sleep(8)
            return self.browser.open(url)

    def readURL(self, url):
        self.LOGGER.info("Reading webpage into memory: %s" % url)
        res = self.openURL(url)
        res = res.read().replace('\\', '')
        return bs4.BeautifulSoup(res)

    def createDir(self, category=None, genre=None, path=None):
        if path:
            if not os.path.exists(path):
                self.LOGGER.info("Creating directory: %s" % path)
                os.makedirs(path)
        else:
            category = self.cleanText(category)
            genre = self.cleanText(genre)
            dirTree = os.path.join(self.sourceDir, category, genre)
            if not os.path.exists(dirTree):
                self.LOGGER.info("Creating directory: %s" % dirTree)
                os.makedirs(dirTree)
            return dirTree

    def cleanText(self, dirtyText):
        return re.sub(self.CLEAN_REGEX, r"", dirtyText)

    @staticmethod
    def defaultSourceDir():
        windowsDir = r'C:\Users\Public\XBMC'
        unixDir    = r'~/XBMC'
        if 'windows' in platform.platform().lower():
            return windowsDir
        return unixDir

    @staticmethod
    def saveMedia(data, path, ext):
        media = '.'.join([path, ext])
        with open(media, 'w') as f:
            f.write(data.encode('ascii', 'ignore'))

    @staticmethod
    def notSubNav(browse):
        """Is category a class of subnav-tabs"""
        try:
            _ = browse.parent['class']
            return False
        except KeyError:
            return True

test = NetflixCollector()
test.collectNetflix()