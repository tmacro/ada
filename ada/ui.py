from .app import app, websocket
from flask import request, jsonify
# import numpy
# from .audio.activity import vad_collector, frame_generator, convert_from_pcm, to_wave
# from .audio.capture import AudioCapture
# from .util.tools import xiter
from .util.log import Log
from .util.conf import config
import collections
# import webrtcvad
import ada.util.rpc
from .util.rpc import Client
import time
_log = Log('ui')

# vad = webrtcvad.Vad(3)

RESPONSE = '''
<div class="talk-bubble tri-right left-top">
	<div class="talktext">
		<p>%s</p>
	</div>
</div>
'''

TRANSLATION = '''
<div class="talk-bubble tri-right right-top">
	<div class="talktext">
		<p>%s</p>
	</div>
</div>
'''

WEATHER = '''
<script>
    function showWeather(data1, data2, data3) {
        if (data1.response.error) ApiError(data1.response.error.description);
        var today = data1.current_observation,
            forecast = data2.forecast.simpleforecast.forecastday;

        // To Be Implemented:  hourly = data3[0].hourly_forecast;

        // Five regions use Fahrenheit by default. For simplicity, assuming
        // these regions are okay with miles and inches as well
        var imperialUnitRegions = ['US', 'BS', 'BZ', 'KY', 'PL'],
            region = today.display_location.country_iso3166;

        var units = 'celsius';
        if (imperialUnitRegions.indexOf(region) > -1) units = 'fahrenheit';

        // Display date/time formats in US format by default unless browser language is available
        var locale = 'en-US';
        if (navigator.language) locale = navigator.language;

        var days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
            currentDay = new Date().toLocaleDateString(locale, {
                weekday: 'long'
            }),
            currentTime = new Date().toLocaleTimeString(locale, {
                hour: '2-digit',
                minute: '2-digit'
            }),
            dateToday = currentDay + ', ' + currentTime;

        $('#city').text(today.display_location.full);
        $('#date').text(dateToday);
        $('#current-conditions').text(today.weather);
        $('#weather-icon').attr('src', today.icon_url.replace('http://', 'https://'));
        $('#humidity').text(today.relative_humidity);

        function showImperialUnits() {
            $('#temperature').text(today.temp_f.toFixed(0));
            $('#degree-units').text('°F | °C');
            $('#precipitation').text(today.precip_today_in + '"');
            $('#wind').text(today.wind_mph + ' mph');
        }

        function showMetricUnits() {
            $('#temperature').text(today.temp_c);
            $('#degree-units').text('°C | °F');
            $('#precipitation').text(today.precip_today_metric + 'mm');
            $('#wind').text(today.wind_kph + ' kph');
        }

        units === 'fahrenheit' ? showImperialUnits() : showMetricUnits();

        // Change units when clicking on the "F | C"
        $('#degree-units').on('click', function (e) {
            if ($('#degree-units').text() === '°C | °F') {
                // convert to fahrenheit
                showImperialUnits();
                $.each($('.high-temp, .low-temp'), function (i, val) {
                    return $(val).html($(val).data('fahrenheit') + '&deg;');
                });
            } else {
                // convert to celsius
                showMetricUnits();
                $.each($('.high-temp, .low-temp'), function (i, val) {
                    return $(val).html($(val).data('celsius') + '&deg;');
                });
            }
        });

        // 6-day forecast
        for (var i = 0; i < 6; i++) {
            if (window.CP.shouldStopExecution(1)) { break; }
            $('#weather-forecast').append('<div class="col s6 m2 forecast-day center-align">\n         <div>' + forecast[i].date.weekday_short + '</div>\n         <div><img src="' + forecast[i].icon_url.replace('http://', 'https://') + '" alt="weather icon"></div>\n         <div class="col s6 high-temp" \n              data-celsius="' + forecast[i].high.celsius + '" \n              data-fahrenheit="' + forecast[i].high.fahrenheit + '">\n           ' + forecast[i].high[units] + '&deg;\n         </div>\n         <div class="col s6 low-temp" \n              data-celsius="' + forecast[i].low.celsius + '" \n              data-fahrenheit="' + forecast[i].low.fahrenheit + '">\n           ' + forecast[i].low[units] + '&deg;\n         </div>\n       </div>');
        }
        window.CP.exitedLoop(1);

        // Initialize tooltips
        $('.tooltipped').tooltip({
            delay: 50
        });

        // Close tooltips on mobile and reinitialize
        $('#weather-card').on('click', function (e) {
            $('.tooltipped').tooltip('close').tooltip({
                delay: 50
            });
        });

        $('.hide').removeClass('hide');
    }

    // Display errors from API calls
    function ApiError(err) {
        $('#error').html('Error: ' + err + '. Please try again later.').show();
        $('.spinner').hide();
    }

    function getWeatherData(location) {
        var key = 'd301cc052928a635',
            todayURL = 'https://api.wunderground.com/api/' + key.replace(/g/g, 'c') + '/conditions/q/' + location + '.json?callback=?',
            hourlyURL = 'https://api.wunderground.com/api/' + key.replace(/g/g, 'c') + '/hourly/q/' + location + '.json?callback=?',
            tenDayForecastURL = 'https://api.wunderground.com/api/' + key.replace(/g/g, 'c') + '/forecast10day/q/' + location + '.json?callback=?';

        $.getJSON(todayURL).done(function (data1) {
            $.getJSON(tenDayForecastURL).done(function (data2) {
                showWeather(data1, data2);
            }).fail(ApiError);
        }).fail(ApiError);
    }

    // Attempt to get location via navigator.geolocation first
    // If that is blocked or fails, use Weather Underground's IP-based location.
    function getLocation() {

        // navigator.geolocation supported and not blocked
        function success(pos) {
            var url = 'https://maps.googleapis.com/maps/api/geocode/json?latlng=' + pos.coords.latitude + ',' + pos.coords.longitude;

            // navigator.geolocation doesn't give us a city name
            // use the Google Maps reverse geocode API to get the city name
            $.getJSON(url, function (data) {
                for (var i = 0; i < data.results.length; i++) {
                    if (window.CP.shouldStopExecution(2)) { break; }
                    if (data.results[i].types.includes('locality')) {
                        getWeatherData(pos.coords.latitude + ',' + pos.coords.longitude);
                        getBackgroundImage(pos.coords.latitude, pos.coords.longitude, data.results[i].formatted_address);
                        return;
                    }
                }
                window.CP.exitedLoop(2);

            }).fail(ApiError);
        }

        // navigator.geolocation blocked/not supported
        function error() {
            getWeatherData('autoip');

            // let users know their location can be more accurate over HTTPS
            if (window.location.protocol === 'http:') $('#weather-card').append('<div class="location-warning">** <small>Open this page over HTTPS and enable \n       location for more accurate results</small></div>');

            function freeGeoIp() {
                $.getJSON('https://freegeoip.net/json?callback=?', function (data) {
                    getBackgroundImage(data.latitude, data.longitude, data.city);
                }).fail(ApiError);
            }

            function ipinfo() {
                $.getJSON('https://ipinfo.io/json?callback=?', function (data) {
                    getBackgroundImage(data.loc.split(',')[0], data.loc.split(',')[1], data.city);
                }).fail(freeGeoIp);
            }

            ipinfo();
        }

        navigator.geolocation.getCurrentPosition(success, error);
    }


    // Display the background image with .load() to determine when it's ready to display
    function displayBackground(bgImage) {
        var img = new Image();
        img.src = bgImage;
        $(img).on('load', function () {
            $('main').css('background-image', 'url("' + bgImage + '")');
            displayFinalPage();
        });
    }

    // callback for determining when async functions are complete
    // if we have a background image and weather data ready, display the page
    function displayFinalPage() {
        if ($('main').css('background-image') !== 'none' && $('#weather-forecast').html() !== "") {
            $('.spinner').hide();
            $('.hide').removeClass('hide');
            $('main').hide().fadeIn(3000);
            $('#weather-card').hide().fadeIn(3000);
        }
    }

    $(getLocation);
</script>
<main>
    <div class="row center-align" id="error"></div>
    <div class="row">
        <div class="col s10 offset-s1">
            <div class="spinner center-align">
                <div class="row">Getting your local weather...</div>
                <div class="preloader-wrapper big active">
                    <div class="spinner-layer spinner-blue-only">
                        <div class="circle-clipper left">
                            <div class="circle"></div>
                        </div>
                        <div class="gap-patch">
                            <div class="circle"></div>
                        </div>
                        <div class="circle-clipper right">
                            <div class="circle"></div>
                        </div>
                    </div>
                </div>
            </div>
            <div id="weather-card" class="card-panel grey-text text-darken-1 hide">
                <div id="location" class="row">
                    <div class="col s12 m6">
                        <h5 id="city"></h5>
                        <h6 id="date"></h6>
                        <h6 id="current-conditions"></h6>
                        <div id="summary">
                            <h6>Precipitation:
                                <span id="preccipitation"></span>
                            </h6>
                            <h6>Humidity:
                                <span id="humidity"></span>
                            </h6>
                            <h6>Wind:
                                <span id="wind"></span>
                            </h6>
                        </div>
                    </div>
                    <div class="col m6 s12 temperature-details">
                        <span>
                            <img id="weather-icon" src="" alt="icon of today's weather">;</span>
                        <span id="temperature"></span>;
                        <span id="degree-units">&deg;F | &deg;C</span>
                    </div>
                </div>
                <!-- <div id="weather-current" class="row hide">
                </div> -->
                <div id="weather-forecast" class="row"></div>
            </div>
        </div>
    </div>
</main>
'''

@app.route('/')
def index():
	return app.send_static_file('index.html')

@app.route('/process', methods = ['POST'])
def process():
	zmqClient = Client(config.zmq.path, config.zmq.pub_key)
	resp = zmqClient.call(request.data)
	text = resp.results.decode('utf-8')
	if 'weather' in text or 'whether' in text:
		return jsonify({
			'translation': TRANSLATION%'Show me the weather',
			'response': WEATHER
			})
	return jsonify({
		"translation": TRANSLATION%resp.results.decode('utf-8'),
		"response": RESPONSE%"Fuck Off!"
	})


# @websocket.route('/audio')
# def audio(ws):
# 	capture = AudioCapture(ws, buffer_ms = 1000)
# 	run = 0
# 	while True:
# 		captured = None
# 		for pcm, raw in xiter(capture(), 5): # Audio in 1 sec chunks
# 			frames = list(frame_generator(30, pcm, 16000))
# 			if list(vad_collector(16000, 30, 300, vad, frames)):
# 				captured = numpy.concatenate((captured, raw)) if not captured is None else raw
# 		ws.send('<--stop-->')
# 		time.sleep(0.5)
# 		_log.debug('Recording done')
# 		if not captured is None:
# 			wav = to_wave(captured, 16000)
# 			with open('test_clip%03i.wav'%run, 'wb'  ) as f:
# 				f.write(wav)
# 			resp = zmqClient.call(wav)
# 			_log.debug(resp.results)
# 			ws.send(resp.results)
# 			run += 1
# 		ws.send('<--start-->')		
		

		
		






		# print('Reported: %s'%rps)
		# 	# if vad.is_speech(frames[index:index+160], 16000):
		# frames = list(frame_generator(10, pcm, 16000))
		# for section in vad_collector(16000, 10, 50, vad, frames):
		# 		print('Detected')
		# samples = numpy.concatenate((samples, raw)) if not samples is None else raw

	# with open('test.wav', 'wb') as file:
	# 	file.write(wav)
	# print(wav)
