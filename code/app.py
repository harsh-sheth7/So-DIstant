import json
from flask_cors import CORS, cross_origin
import cv2
import imutils
import os
from flask import Flask, render_template, Response, send_from_directory, request
from imutils.video import FPS

from detect import detect_people, draw_people, draw_metrics

app = Flask(__name__)
app.config.from_pyfile('config.py')

settings = ['MODEL_PATH', 'MIN_CONF', 'NMS_THRESH', 'DISPLAY', 'THRESHOLD', 'USE_GPU', 'ALERT', 'MAIL', 'URL',
            'MIN_DISTANCE', 'CV_INP_WIDTH', 'CV_INP_HEIGHT', 'WEIGHTS', 'CFG', 'VIDEO_PATH']


def getSettings(config_dict):
    return {key: config_dict[key] for key in settings}


print(getSettings(app.config))

labels = [
    'JAN', 'FEB', 'MAR', 'APR',
    'MAY', 'JUN', 'JUL', 'AUG',
    'SEP', 'OCT', 'NOV', 'DEC'
]

values = [
    967.67, 1190.89, 1079.75, 1349.19,
    2328.91, 2504.28, 2873.83, 4764.87,
    4349.29, 6458.30, 9907, 16297
]

colors = [
    "#F7464A", "#46BFBD", "#FDB45C", "#FEDCBA",
    "#ABCDEF", "#DDDDDD", "#ABCABC", "#4169E1",
    "#C71585", "#FF4500", "#FEDCBA", "#46BFBD"]


def gen_frames(filename):
    with app.app_context():
        labelsPath = os.path.sep.join([app.config['MODEL_PATH'], "coco.names"])
        LABELS = open(labelsPath).read().strip().split("\n")

        weightsPath = os.path.sep.join([app.config['MODEL_PATH'], app.config['WEIGHTS']])
        configPath = os.path.sep.join([app.config['MODEL_PATH'], app.config['CFG']])

        net = cv2.dnn.readNetFromDarknet(configPath, weightsPath)

        if app.config['USE_GPU']:
            print("[INFO] Using GPU")
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
        else:
            print("[INFO] Using CPU")
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        ln = net.getLayerNames()
        ln = [ln[i[0] - 1] for i in net.getUnconnectedOutLayers()]

        cap = cv2.VideoCapture(app.config['VIDEO_PATH'] + filename + ".mp4")
        fps = FPS().start()

        while True:
            success, frame = cap.read()
            if not success:
                break
            frame = imutils.resize(frame, width=700, height=700)
            results, no_of_people = detect_people(frame, net, ln, personIdx=LABELS.index("person"))
            violations = draw_people(frame, results)
            draw_metrics(frame, violations, no_of_people)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield "{\"violations\": %d}" % len(violations)
            yield b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
            # time.sleep(0.1)
            fps.update()
        fps.stop()
        print("----------------------------")
        print("[INFO] Elapsed time: {:.2f}".format(fps.elapsed()))
        print("[INFO] Approx. FPS: {:.2f}".format(fps.fps()))


@app.route('/video_feed/<path:filename>')
def video_feed(filename):
    return Response(gen_frames(filename), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/line')
def line():
    line_labels = labels
    line_values = values
    return render_template('line_chart.html', title='Surveillance - Social distancing metrics', max=17000,
                           labels=line_labels, values=line_values)


@app.route('/download/<path:filename>', methods=['GET', 'POST'])
@cross_origin(origin='localhost')
def download(filename):
    uploads = os.path.join(app.root_path, app.config['VIDEO_PATH'] + "output/")
    return send_from_directory(directory=uploads, filename=filename + ".mp4",mimetype='application/octet-stream', as_attachment=True)


@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'GET':
        return json.dumps(getSettings(app.config))
    else:
        data = request.json
        if 'MODEL_PATH' in data:
            app.config['MODEL_PATH'] = data['MODEL_PATH'],
        if 'MIN_CONF' in data:
            app.config['MIN_CONF'] = data['MIN_CONF']
        if 'NMS_THRESH' in data:
            app.config['NMS_THRESH'] = data['NMS_THRESH']
        if 'DISPLAY' in data:
            app.config['DISPLAY'] = data['DISPLAY']
        if 'THRESHOLD' in data:
            app.config['THRESHOLD'] = data['THRESHOLD']
        if 'USE_GPU' in data:
            app.config['USE_GPU'] = data['USE_GPU']
        if 'ALERT' in data:
            app.config['ALERT'] = data['ALERT']
        if 'MAIL' in data:
            app.config['MAIL'] = data['MAIL']
        if 'URL' in data:
            app.config['URL'] = data['URL']
        if 'MIN_DISTANCE' in data:
            app.config['MIN_DISTANCE'] = data['MIN_DISTANCE']
        if 'CV_INP_WIDTH' in data:
            app.config['CV_INP_WIDTH'] = data['CV_INP_WIDTH']
        if 'CV_INP_HEIGHT' in data:
            app.config['CV_INP_HEIGHT'] = data['CV_INP_HEIGHT']
        if 'WEIGHTS' in data:
            app.config['WEIGHTS'] = data['WEIGHTS']
        if 'CFG' in data:
            app.config['CFG'] = data['CFG']
        if 'VIDEO_PATH' in data:
            app.config['VIDEO_PATH'] = data['VIDEO_PATH']
        return json.dumps(getSettings(app.config))


if __name__ == '__main__':
    app.run(debug=True)
