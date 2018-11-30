#===============================================================================
# LICENSE Retrospect-Framework - CC BY-NC-ND
#===============================================================================
# This work is licenced under the Creative Commons
# Attribution-Non-Commercial-No Derivative Works 3.0 Unported License. To view a
# copy of this licence, visit http://creativecommons.org/licenses/by-nc-nd/3.0/
# or send a letter to Creative Commons, 171 Second Street, Suite 300,
# San Francisco, California 94105, USA.
#===============================================================================

from urihandler import UriHandler
from logger import Logger
from regexer import Regexer
from streams.adaptive import Adaptive


class M3u8:
    def __init__(self):
        pass

    @staticmethod
    def get_subtitle(url, proxy=None, play_list_data=None, append_query_string=True, language=None):  # NOSONAR
        data = play_list_data or UriHandler.open(url, proxy)
        regex = r'(#\w[^:]+)[^\n]+TYPE=SUBTITLES[^\n]*LANGUAGE="(\w+)"[^\n]*\W+URI="([^"]+.m3u8[^"\n\r]*)'
        sub = ""

        qs = None
        if append_query_string and "?" in url:
            base, qs = url.split("?", 1)
            Logger.info("Going to append QS: %s", qs)
        elif "?" in url:
            base, qs = url.split("?", 1)
            Logger.info("Ignoring QS: %s", qs)
            qs = None
        else:
            base = url

        needles = Regexer.do_regex(regex, data)
        url_index = 2
        language_index = 1
        base_url_logged = False
        base_url = base[:base.rindex("/")]
        for n in needles:
            if language is not None and n[language_index] != language:
                Logger.debug("Found incorrect language: %s", n[language_index])
                continue

            if "://" not in n[url_index]:
                if not base_url_logged:
                    Logger.debug("Using base_url %s for M3u8", base_url)
                    base_url_logged = True
                sub = "%s/%s" % (base_url, n[url_index])
            else:
                if not base_url_logged:
                    Logger.debug("Full url found in M3u8")
                    base_url_logged = True
                sub = n[url_index]

            if qs is not None and sub.endswith("?null="):
                sub = sub.replace("?null=", "?%s" % (qs, ))
            elif qs is not None and "?" in sub:
                sub = "%s&%s" % (sub, qs)
            elif qs is not None:
                sub = "%s?%s" % (sub, qs)

        return sub

    @staticmethod
    def set_input_stream_addon_input(strm, proxy=None, headers=None,
                                     license_key=None, license_type=None,
                                     max_bit_rate=None,
                                     persist_storage=False,
                                     service_certificate=None):
        return Adaptive.set_input_stream_addon_input(strm, proxy, headers,
                                                     manifest_type="hls",
                                                     license_key=license_key,
                                                     license_type=license_type,
                                                     max_bit_rate=max_bit_rate,
                                                     persist_storage=persist_storage,
                                                     service_certificate=service_certificate)

    @staticmethod
    def get_license_key(key_url, key_type="R", key_headers=None, key_value=None):
        # type: (str, str, dict, str) -> str

        return Adaptive.get_license_key(key_url,
                                        key_type=key_type,
                                        key_headers=key_headers,
                                        key_value=key_value)

    @staticmethod
    def get_streams_from_m3u8(url, proxy=None, headers=None,                  # NOSONAR
                              append_query_string=False, map_audio=False,
                              play_list_data=None):
        """ Parsers standard M3U8 lists and returns a list of tuples with streams and bitrates that
        can be used by other methods.

        @param headers:           (dict) Possible HTTP Headers
        @param proxy:             (Proxy) The proxy to use for opening
        @param url:               (String) The url to download
        @param append_query_string: (boolean) should the existing query string be appended?
        @param map_audio:          (boolean) map audio streams
        @param play_list_data:      (string) data of an already retrieved M3u8

        Can be used like this:

            part = item.create_new_empty_media_part()
            for s, b in M3u8.get_streams_from_m3u8(m3u8Url, self.proxy):
                item.complete = True
                # s = self.get_verifiable_video_url(s)
                part.append_media_stream(s, b)

        """

        streams = []

        data = play_list_data or UriHandler.open(url, proxy, additional_headers=headers)
        Logger.trace(data)

        qs = None
        if append_query_string and "?" in url:
            base, qs = url.split("?", 1)
            Logger.info("Going to append QS: %s", qs)
        elif "?" in url:
            base, qs = url.split("?", 1)
            Logger.info("Ignoring QS: %s", qs)
            qs = None
        else:
            base = url

        Logger.debug("Processing M3U8 Streams: %s", url)

        # If we need audio
        if map_audio:
            audio_needle = r'(#\w[^:]+):TYPE=AUDIO()[^\r\n]+ID="([^"]+)"[^\n\r]+URI="([^"]+.m3u8[^"]*)"'
            needles = Regexer.do_regex(audio_needle, data)
            needle = r'(#\w[^:]+)[^\n]+BANDWIDTH=(\d+)\d{3}(?:[^\r\n]*AUDIO="([^"]+)"){0,1}[^\n]*\W+([^\n]+.m3u8[^\n\r]*)'
            needles += Regexer.do_regex(needle, data)
            type_index = 0
            bitrate_index = 1
            id_index = 2
            url_index = 3
        else:
            needle = r"(#\w[^:]+)[^\n]+BANDWIDTH=(\d+)\d{3}[^\n]*\W+([^\n]+.m3u8[^\n\r]*)"
            needles = Regexer.do_regex(needle, data)
            type_index = 0
            bitrate_index = 1
            url_index = 2

        audio_streams = {}
        base_url_logged = False
        base_url = base[:base.rindex("/")]
        for n in needles:
            # see if we need to append a server path
            Logger.trace(n)

            if "#EXT-X-I-FRAME" in n[type_index]:
                continue

            if "://" not in n[url_index]:
                if not base_url_logged:
                    Logger.debug("Using baseUrl %s for M3u8", base_url)
                    base_url_logged = True
                stream = "%s/%s" % (base_url, n[url_index])
            else:
                if not base_url_logged:
                    Logger.debug("Full url found in M3u8")
                    base_url_logged = True
                stream = n[url_index]
            bitrate = n[bitrate_index]

            if qs is not None and stream.endswith("?null="):
                stream = stream.replace("?null=", "?%s" % (qs, ))
            elif qs is not None and "?" in stream:
                stream = "%s&%s" % (stream, qs)
            elif qs is not None:
                stream = "%s?%s" % (stream, qs)

            if map_audio and "#EXT-X-MEDIA" in n[type_index]:
                # noinspection PyUnboundLocalVariable
                Logger.debug("Found audio stream: %s -> %s", n[id_index], stream)
                audio_streams[n[id_index]] = stream
                continue

            if map_audio:
                streams.append((stream, bitrate, audio_streams.get(n[id_index]) or None))
            else:
                streams.append((stream, bitrate))

        Logger.debug("Found %s substreams in M3U8", len(streams))
        return streams
