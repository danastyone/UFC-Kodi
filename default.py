import sys, xbmcgui, xbmcplugin, xbmcaddon
import os, requests, re, json
from urllib import urlencode 
from urlparse import parse_qsl
import pickle


addon           = xbmcaddon.Addon(id='plugin.video.ufc')
addon_url       = sys.argv[0]
addon_handle    = int(sys.argv[1])
addon_icon      = addon.getAddonInfo('icon')
addon_BASE_PATH = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
#COOKIE_FILE     = os.path.join(addon_BASE_PATH, 'cookies.lwp')
#CACHE_FILE      = os.path.join(addon_BASE_PATH, 'data.json')
#SWAP_FILE      = os.path.join("/tmp/", 'swap.json')
TOKEN_FILE = os.path.join("/tmp/","auth_token.txt")


###SET Background?
#xbmcplugin.setPluginFanart(int(sys.argv[1]), 'special://home/addons/plugins/video/Apple movie trailers II/fanart.png', color2='0xFFFF3300')

BW = 1080
BW = addon.getSetting('bandwidth')
resolutions = [(1080,"1920x1080"),(720,"1280x720"),(504, "896x504"),(360 , "640x360"),(288, "512x288")]

urls = {
        "home" : "https://dce-frontoffice.imggaming.com/api/v2/content/home?bpp=10&bp=1&rpp=25&displayGeoblockedLive=false&displaySectionLinkBuckets=show",
        "library" : "https://dce-frontoffice.imggaming.com/api/v2/content/browse?bpp=10&bp=1&rpp=25&displaySectionLinkBuckets=show",
        "url247" : "https://dce-frontoffice.imggaming.com/api/v2/event/live?rpp=3",
        "favourites" : "https://dce-frontoffice.imggaming.com/api/v2/favourite/vods?rpp=25",
        "history": "https://dce-frontoffice.imggaming.com/api/v2/customer/history/vod?p=1&rpp=25"
        }

auth_url = "https://dce-frontoffice.imggaming.com/api/v2/login"

headers={
    "content-type": "application/json",
    "realm": "dce.ufc",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36",
    "x-api-key": "857a1e5d-e35e-4fdf-805b-a87b6f8364bf"
  }

def get_creds():
    """Get username and password. Return dict of username and password"""

    if len(addon.getSetting('username')) == 0 or len(addon.getSetting('password')) == 0:
        return None

    return {
        'username': addon.getSetting('username'),  
        'password': addon.getSetting('password')
    }

def get_auth_token():
    """Take in the credentials as dict['username', 'password'] and return the Auth token as string with the bearer keyword ready to be used in the header"""
    
    creds = get_creds()
    credentials = json.dumps({"id":creds['username'],"secret":creds['password']})

    session = requests.Session()
    session.headers = headers
    response = session.post(auth_url, data=credentials)

    if response.status_code == 201:
        token = "Bearer " + response.json()["authorisationToken"]
        session.close()
        return token
    
    else:
        xbmc.log("Could not get Auth Token, Session text: {0}".format(str(session.json())),level=xbmc.LOGERROR)
        return False


def get_web_data(url):
    """Grab the web data from the url"""

    token = get_token()


    session = requests.Session()
    headers_this_session = headers
    headers_this_session["authorization"] = token
    session.headers = headers_this_session
    
    response = session.get(url, headers=headers_this_session)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:  #if the token gives back unauthorized, it's old. Delete it and rerun the method
        os.remove(TOKEN_FILE)
        get_web_data(url)
    else:
        xbmc.log("Could not get data, line 80. Response: {0}\r\nText: {1}".format(response.status_code, response.text),level=xbmc.LOGERROR)
        return None

def get_token():
    """Get the token either from the file saved or by getting a new one if the file doesn't exist"""
    if not os.path.isfile(TOKEN_FILE): #if bearer token file does not exist
        token = get_auth_token()
    else:
        token = pickle.load(open(TOKEN_FILE, 'rb'))

    return token


def router(paramstring):
    """Router for kodi to select the menu item and route appropriately. """ 
    
    params = dict(parse_qsl(paramstring))
    
    
    
    if params:
        action = params['action']
        if action == 'listing':
            menu_data=get_categories(params['u'])
            build_menu(menu_data)
        elif action == 'play':
            play_video(params['i'],params['t'])
        else:
            pass
    else:
        build_initial_menu()
          #menu_data=get_categories(urls["home"])
          #build_menu(menu_data)
          



def get_categories(url):
    """Put items into readable array of dict, and return the array for building the menu"""
    data = get_web_data(url) ###Scrape the url data

    #keywords = ["contentList","vods","subEvents","events"]
    keywords = ["contentList","vods","events"]
    
    
    extract = []
    
    for keyword in keywords:
        iter_object = gen_dict_extract(keyword, data) ##create the iter object
        
        for half_parsed_list in iter_object: #
            extract.append(half_parsed_list)
    
    clean_extract = clean_iter_data(extract)

 
    ### REmove this for the moment extract = gen_dict_extract(keywords, data) ###Grab all items in nested dict that have "contentList as key"   
    my_listings = []
    for i in clean_extract:        
        if i.get("type") == 'PLAYLIST':
            listing = {
                'type' : i.get("type"),
                'coverUrl' : i.get("coverUrl"),
                'smallCoverUrl' : i.get("smallCoverUrl"),
                'title' : i.get("title"),
                'description' : i.get("description"),
                'id' : i.get("id")
                }
            my_listings.append(listing)
        if i.get("type") == 'VOD':
            listing = {
                'type' : i.get("type"),
                'thumbnailUrl' : i.get("thumbnailUrl"),
                #'posterUrl' : i.get("posterUrl"),
                'duration' : i.get("duration"),
                'title' : i.get("title"),
                'description' : i.get("description"),
                'id' : i.get("id"),
                'duration' : i.get("duration")
                }
            if i.get("posterUrl"):
                listing["posterUrl"] = i.get("posterUrl")
            else:
                listing["posterUrl"] = listing["thumbnailUrl"]

            my_listings.append(listing)

    return my_listings


def clean_iter_data(data):
    """Takes in iter data which is mess and returns list of dict items"""
    newlist = []
    newlist = [item for data in data for item in data]
    return_list = []    
    for item in newlist:
        if type(item) is dict:
            return_list.append(item)

    return return_list
            
                
def build_menu(itemData):     
    """ Takes in array of dict, using this array builds a menu to display in Kodi"""
    for my_item in itemData:
        if my_item["type"] == 'VOD':
            kodi_item = xbmcgui.ListItem(label=my_item["title"])
            kodi_item.setArt({  'thumb': my_item["thumbnailUrl"], 
                                'icon' :  my_item["thumbnailUrl"], 
                                'landscape': my_item["posterUrl"], 
                                'poster' : my_item["posterUrl"], 
                                'banner': my_item["posterUrl"], 
                                'fanart': my_item["posterUrl"]})
            kodi_item.setInfo(type='video', infoLabels={'plot': my_item.get("description"), 'duration': my_item.get("duration") })
                                
            url = '{0}?action=play&i={1}&t={2}'.format(addon_url, my_item["id"], my_item["title"])
            xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, False ) ###last false is if it is a directory

    ###Thats it create the folder structure
    xbmcplugin.endOfDirectory(addon_handle)



def build_initial_menu():
    """Builds the initial menus for UFC"""

    for item in urls:   
        kodi_item = xbmcgui.ListItem(label=item)
        kodi_item.setInfo(type='video', infoLabels={'plot': "UFC {0}".format(str(item))} )
        url = '{0}?action=listing&u={1}'.format(addon_url, urls[item])
        xbmcplugin.addDirectoryItem(addon_handle, url, kodi_item, True ) ###last false is if it is a directory
    xbmcplugin.endOfDirectory(addon_handle)








def gen_dict_extract(key, var):
    """Find all items with value "key" in dict var, and return an iterable with all the key items, need to iter using
        for x in generator, x[0]"""
    if hasattr(var,'items'):   
        for k, v in var.items():
            if k in key:             
                yield v
            if isinstance(v, dict):
                for result in gen_dict_extract(key, v):                   
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(key, d):     
                        yield result

def play_video(v_id, v_title):
    # Fetch the stream url and play the video
    status, stream = publish_point({'id': v_id })
    
    if status == 400:
        if post_auth(get_creds()):
            status, stream = publish_point({ 'id': v_id })
        else:
            dialog = xbmcgui.Dialog()
            dialog.ok('Authorization Error', 'Authorization to UFC Fight Pass failed.')
    
    
    
    v_token = get_token()
    
    encode_string = {"User-Agent": headers["user-agent"], "authorization": v_token, "content-type": "video/MP2T" }
    my_encoding = urlencode(encode_string)

    try:
        #pass
        stream = stream + '|' +my_encoding
        item = xbmcgui.ListItem(label=v_title)
        xbmc.Player().play(stream, item)
    except:
        dialog = xbmcgui.Dialog()
        dialog.ok('Playback Error', 'Unable to play video: ' + v_title)
        #dialog.ok('Playback Error', 'Video Stream' + stream)
                        
                        
                        
def publish_point(video):
    """??Takes in Video Dict, queries website publishpoint with video info (video id), 
    get a response that includes a path,returns (status code, path to video)"""
    
    url = 'https://dce-frontoffice.imggaming.com/api/v2/stream/vod/'
    start_url = "" ## Start url string for final response. 
#    payload = {
#        'eventId': str(video['id']),
#        'sportId': '0',  
#        'propertyId': '0',
#        'tournamentId':'0', 
#        'displayGeoblockedLive': 'false' ###added this 24/01/2019          
 #   }
    
    s = requests.Session()
    header_this_session = headers
    header_this_session["authorization"] = str(get_token())
    s.headers = header_this_session
    
    
    resp = s.get(url+str(video['id']), headers=header_this_session) #changed params=payload to params=str(video['id'])
    # normally status 400 if have an expired session
    status = resp.status_code
    result = resp.json()
    if not result:
        return status, None
    
    

    if "dve-api" in result['playerUrlCallback']:
        resp = s.get(result['playerUrlCallback'], headers = header_this_session)
        status = resp.status_code
        result= resp.json()
        o_path = result["hls"]["url"]
        start_url = o_path
    
        if "dve-streams.akamaized.net" in o_path:
            resp = s.get(o_path, headers = header_this_session)
            result = resp.text
            o_path = return_FQDN_for_res(result,start_url)

    else:
        o_path = result['playerUrlCallback']
   


    return status, o_path

def return_FQDN_for_res(result, start_url):
    
    ###The expression bellow needs to be better. In some instances it gets an extra value at the end###
    my_expression = "(.*?)\w+\.\w+\?"
    matches = re.match(my_expression,start_url)
    url_start = matches.group(1)
    url_end = ""

    splits = iter(result.split('\n'))    

    for line in splits:
        for resolution in resolutions:
            if BW >= resolution[0]:
                if resolution[1] in line:
                    url_end =  next(splits)
                    return url_start +   url_end 




if __name__ == '__main__':     
    router(sys.argv[2][1:])






