from flask import Flask
from flask import abort, redirect, url_for, request, render_template, make_response
from werkzeug import secure_filename
import time
import echonest.remix.audio as audio
import pyrax
import os

app = Flask(__name__, static_folder="public", static_url_path="/static")
pyrax.set_credential_file('pyrax.conf')
cf = pyrax.cloudfiles

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if request.method == 'POST':
        #Get the file
        audiofile = request.files['audio']
        fname = 'tmp/' + str(long(time.time())) + secure_filename(audiofile.filename)
        audiofile.save(fname)

        remixfile = audio.LocalAudioFile(fname)
        beats = remixfile.analysis.beats

        #https://github.com/echonest/remix/blob/master/examples/sorting/sorting.py
        def sorting_function(chunk):
            return chunk.mean_loudness()

        sortedbeats = sorted(beats, key=sorting_function)

        out = audio.getpieces(remixfile, sortedbeats)

        audioname = str(long(time.time())) + 'sorted' + secure_filename(audiofile.filename) + '.mp3'
        outfname = 'tmp/' + audioname
        out.encode(outfname, mp3=True)

        #Upload to rackspace
        chksum = pyrax.utils.get_checksum(outfname)
        cf.upload_file("beatsorter", outfname, etag=chksum)

        #os.remove(fname)
        #os.remove(outfname)
        return redirect(url_for('getaudiofile', filename=audioname))

@app.route('/audio/<filename>')
def getaudiofile(filename):
    obj = cf.fetch_object("beatsorter", filename)
    resp = make_response(obj, 200)
    resp.headers['Content-type'] = 'audio/wav'
    return resp

if __name__ == '__main__':
    app.run(debug=True)
