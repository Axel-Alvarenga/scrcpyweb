from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import os
import json
import re
import sys
import threading
import webbrowser
import time
import atexit
import signal
import psutil

# ============================================================
#   DETERMINAR RUTAS
# ============================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    CONFIG_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_DIR = BASE_DIR

FRONTEND_FOLDER = os.path.join(BASE_DIR, 'frontend', 'build')
if not os.path.exists(FRONTEND_FOLDER):
    FRONTEND_FOLDER = r'C:\Users\chuva\OneDrive\Desktop\scrpywebexe\frontend\build'

app = Flask(__name__, static_folder=FRONTEND_FOLDER, static_url_path='')
CORS(app)

CONFIG_FILE = os.path.join(CONFIG_DIR, 'scrcpy_config.json')
IP_FILE = os.path.join(CONFIG_DIR, 'scrcpy_ip.txt')
PUERTO = '5555'

# ============================================================
#   SISTEMA DE CIERRE AUTOMÁTICO
# ============================================================
def cerrar_todo():
    """Cierra todos los procesos hijos cuando termina el programa"""
    try:
        proceso_actual = psutil.Process()
        hijos = proceso_actual.children(recursive=True)
        
        for hijo in hijos:
            try:
                hijo.terminate()
            except:
                pass
        
        time.sleep(1)
        
        for hijo in hijos:
            try:
                hijo.kill()
            except:
                pass
                
        print("🧹 Todos los procesos cerrados correctamente.")
    except Exception as e:
        print(f"Error al cerrar procesos: {e}")

def manejar_senal(sig, frame):
    """Maneja señales de cierre (Ctrl+C, etc.)"""
    print("\n🛑 Recibida señal de cierre...")
    cerrar_todo()
    sys.exit(0)

# Registrar el cierre automático
atexit.register(cerrar_todo)
signal.signal(signal.SIGINT, manejar_senal)
signal.signal(signal.SIGTERM, manejar_senal)

# ============================================================
#   FUNCIONES DE UTILIDAD
# ============================================================
def ejecutar_comando(comando):
    try:
        resultado = subprocess.run(
            comando, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=30
        )
        return {
            'success': True,
            'stdout': resultado.stdout,
            'stderr': resultado.stderr,
            'code': resultado.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Tiempo de espera agotado'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def obtener_ip_guardada():
    try:
        with open(IP_FILE, 'r') as f:
            return f.read().strip()
    except:
        return '192.168.100.47'

def guardar_ip(ip):
    try:
        with open(IP_FILE, 'w') as f:
            f.write(ip)
    except:
        pass

def obtener_opciones():
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            'calidad': '--max-size=1080 --max-fps=30 --video-bit-rate=4M',
            'ventana': '',
            'opciones_extra': ''
        }

def guardar_opciones(opciones):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(opciones, f, indent=2)
    except:
        pass

def obtener_opciones_completas():
    opciones = obtener_opciones()
    opciones_completas = []
    if opciones.get('calidad'):
        opciones_completas.append(opciones['calidad'])
    if opciones.get('ventana'):
        opciones_completas.append(opciones['ventana'])
    if opciones.get('opciones_extra'):
        opciones_completas.append(opciones['opciones_extra'])
    return ' '.join([o for o in opciones_completas if o])

def matar_scrcpy():
    try:
        subprocess.run('taskkill /f /im scrcpy.exe', shell=True, capture_output=True)
        return True
    except:
        return False

def abrir_scrcpy_interno():
    try:
        matar_scrcpy()
        opciones_completas = obtener_opciones_completas()
        comando = f'start scrcpy {opciones_completas}'
        subprocess.Popen(comando, shell=True)
        return True
    except:
        return False

# ============================================================
#   SERVIR FRONTEND
# ============================================================
@app.route('/')
def serve_frontend():
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        return f'Error: {e}', 404

@app.route('/<path:path>')
def serve_static(path):
    try:
        return send_from_directory(app.static_folder, path)
    except Exception as e:
        return f'Error: {e}', 404

# ============================================================
#   API ENDPOINTS
# ============================================================
@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({'status': 'ok', 'message': 'Servidor scrcpy-web funcionando'})

@app.route('/api/ip', methods=['GET'])
def get_ip():
    return jsonify({'ip': obtener_ip_guardada()})

@app.route('/api/ip', methods=['POST'])
def set_ip():
    data = request.json
    nueva_ip = data.get('ip', '')
    if not nueva_ip:
        return jsonify({'error': 'IP no válida'}), 400
    guardar_ip(nueva_ip)
    return jsonify({'success': True, 'ip': nueva_ip})

@app.route('/api/activar-wifi', methods=['POST'])
def activar_wifi():
    try:
        resultado = ejecutar_comando('adb devices')
        if 'device' not in resultado['stdout'] or 'emulator' in resultado['stdout']:
            return jsonify({
                'success': False, 
                'message': '❌ No se detecta ningún dispositivo USB. Conecta tu teléfono por USB y asegúrate de que la depuración USB está activada.'
            })
        
        resultado = ejecutar_comando('adb tcpip 5555')
        
        if 'restarting in TCP mode port' in resultado['stdout']:
            return jsonify({
                'success': True, 
                'message': '✅ Modo WiFi activado. Ahora puedes desconectar el USB y conectar por WiFi.',
                'output': resultado['stdout']
            })
        else:
            return jsonify({
                'success': False, 
                'message': '❌ No se pudo activar el modo WiFi. Asegúrate de que la depuración USB está activada.'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/cerrar-servidor', methods=['POST'])
def cerrar_servidor():
    """Cierra el servidor cuando el usuario cierra el navegador"""
    def cerrar():
        time.sleep(1)
        print("🛑 Navegador cerrado. Cerrando servidor...")
        cerrar_todo()
        os._exit(0)
    
    threading.Thread(target=cerrar, daemon=True).start()
    return jsonify({'success': True, 'message': 'Cerrando servidor...'})

@app.route('/api/conectar', methods=['POST'])
def conectar():
    try:
        ip = obtener_ip_guardada()
        ejecutar_comando(f'adb disconnect {ip}:{PUERTO}')
        resultado = ejecutar_comando(f'adb connect {ip}:{PUERTO}')
        
        if resultado['success']:
            verificar = ejecutar_comando('adb devices')
            if ip in verificar['stdout']:
                matar_scrcpy()
                abrir_scrcpy_interno()
                return jsonify({'success': True, 'message': f'Conectado a {ip}:{PUERTO}'})
        
        return jsonify({'success': False, 'message': 'No se pudo conectar'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/desconectar', methods=['POST'])
def desconectar():
    try:
        ip = obtener_ip_guardada()
        ejecutar_comando(f'adb disconnect {ip}:{PUERTO}')
        matar_scrcpy()
        return jsonify({'success': True, 'message': 'Desconectado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/abrir-scrcpy', methods=['POST'])
def abrir_scrcpy():
    try:
        if abrir_scrcpy_interno():
            return jsonify({'success': True, 'message': 'Scrcpy iniciado'})
        else:
            return jsonify({'success': False, 'message': 'No se pudo iniciar scrcpy'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/cerrar-scrcpy', methods=['POST'])
def cerrar_scrcpy():
    try:
        matar_scrcpy()
        return jsonify({'success': True, 'message': 'Scrcpy cerrado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/estado', methods=['GET'])
def estado():
    try:
        ip = obtener_ip_guardada()
        resultado = ejecutar_comando('adb devices')
        conectado = ip in resultado['stdout']
        return jsonify({
            'conectado': conectado,
            'ip': ip,
            'dispositivos': resultado['stdout']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dispositivos', methods=['GET'])
def dispositivos():
    resultado = ejecutar_comando('adb devices')
    return jsonify({'dispositivos': resultado['stdout']})

@app.route('/api/ip-pc', methods=['GET'])
def ip_pc():
    resultado = ejecutar_comando('ipconfig | findstr "IPv4"')
    if resultado['success']:
        ips = re.findall(r'(\d+\.\d+\.\d+\.\d+)', resultado['stdout'])
        ips = [ip for ip in ips if ip != '127.0.0.1']
        return jsonify({'ips': ips})
    return jsonify({'error': 'No se pudo obtener IP'})

@app.route('/api/opciones', methods=['GET'])
def get_opciones():
    opciones = obtener_opciones()
    return jsonify({
        'raw': opciones,
        'completo': obtener_opciones_completas()
    })

@app.route('/api/opciones', methods=['POST'])
def set_opciones():
    data = request.json
    opciones = obtener_opciones()
    if 'calidad' in data:
        opciones['calidad'] = data['calidad']
    if 'ventana' in data:
        opciones['ventana'] = data['ventana']
    if 'opciones_extra' in data:
        opciones['opciones_extra'] = data['opciones_extra']
    guardar_opciones(opciones)
    return jsonify({
        'success': True, 
        'opciones': opciones,
        'completo': obtener_opciones_completas()
    })

@app.route('/api/opciones/quitar', methods=['POST'])
def quitar_opcion():
    data = request.json
    patron = data.get('patron', '')
    opciones = obtener_opciones()
    for key in ['calidad', 'ventana', 'opciones_extra']:
        if opciones.get(key):
            partes = opciones[key].split()
            nuevas = [p for p in partes if patron.lower() not in p.lower()]
            opciones[key] = ' '.join(nuevas)
    guardar_opciones(opciones)
    return jsonify({
        'success': True, 
        'opciones': opciones,
        'completo': obtener_opciones_completas()
    })

@app.route('/api/opciones/restablecer', methods=['POST'])
def restablecer_opciones():
    guardar_opciones({
        'calidad': '--max-size=1080 --max-fps=30 --video-bit-rate=4M',
        'ventana': '',
        'opciones_extra': ''
    })
    return jsonify({
        'success': True, 
        'message': 'Opciones restablecidas',
        'completo': obtener_opciones_completas()
    })

@app.route('/api/instalar-apk', methods=['POST'])
def instalar_apk():
    data = request.json
    ruta = data.get('ruta', '')
    if not os.path.exists(ruta):
        return jsonify({'error': 'El archivo no existe'}), 400
    resultado = ejecutar_comando(f'adb install "{ruta}"')
    return jsonify({
        'success': resultado['success'],
        'output': resultado['stdout'],
        'error': resultado.get('stderr', '')
    })

@app.route('/api/scrcpy/opciones-disponibles', methods=['GET'])
def opciones_disponibles():
    opciones = {
        'video': [
            '--max-size=N', '--max-fps=N', '--video-bit-rate=N',
            '--video-codec=h264/h265/av1', '--crop=W:H:X:Y',
            '--angle=N', '--lock-video-orientation'
        ],
        'audio': [
            '--no-audio', '--audio-codec=opus/aac/flac',
            '--audio-bit-rate=N', '--audio-source=output/mic/playback',
            '--audio-dup'
        ],
        'ventana': [
            '--fullscreen', '--always-on-top', '--window-borderless',
            '--window-x=N --window-y=N', '--window-width=N --window-height=N',
            '--window-title="TEXT"', '--disable-screensaver'
        ],
        'input': [
            '--keyboard=sdk/uhid/aoa', '--mouse=sdk/uhid/aoa',
            '--gamepad=uhid/aoa/disabled', '--no-control'
        ],
        'otros': [
            '--turn-screen-off', '--stay-awake', '--show-touches',
            '--record=archivo.mp4', '--no-display', '--tcpip', '--otg'
        ]
    }
    return jsonify(opciones)

# ============================================================
#   ABRIR NAVEGADOR Y CIERRE
# ============================================================
def open_browser():
    time.sleep(2)
    webbrowser.open('http://localhost:5000')

# ============================================================
#   MAIN
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("  📱 SCRCPY WEB - SERVIDOR INICIADO")
    print("=" * 60)
    print(f"  📁 Frontend: {FRONTEND_FOLDER}")
    print(f"  🌐 Abre tu navegador en: http://localhost:5000")
    print(f"  ⏹️  Cierra el navegador o presiona CTRL+C para cerrar")
    print("=" * 60)
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 Cerrando servidor...")
        cerrar_todo()
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        cerrar_todo()
        sys.exit(1)