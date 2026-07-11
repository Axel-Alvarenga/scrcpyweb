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

# ============================================================
#   RUTAS DINÁMICAS
# ============================================================
def obtener_ruta_base():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def obtener_ruta_frontend():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'frontend', 'build')
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'build')

# ============================================================
#   CONFIGURACIÓN
# ============================================================
BASE_DIR = obtener_ruta_base()
FRONTEND_FOLDER = obtener_ruta_frontend()

CONFIG_FILE = os.path.join(BASE_DIR, 'scrcpy_config.json')
IP_FILE = os.path.join(BASE_DIR, 'scrcpy_ip.txt')
DEVICES_FILE = os.path.join(BASE_DIR, 'scrcpy_devices.json')

RUTA_SCRCPY = os.path.join(BASE_DIR, 'tools', 'scrcpy', 'scrcpy.exe')
RUTA_ADB = os.path.join(BASE_DIR, 'tools', 'scrcpy', 'adb.exe')

PUERTO = '5555'

app = Flask(__name__, static_folder=FRONTEND_FOLDER, static_url_path='')
CORS(app)

# ============================================================
#   FUNCIONES DE DISPOSITIVOS
# ============================================================
def obtener_dispositivos():
    try:
        with open(DEVICES_FILE, 'r') as f:
            return json.load(f)
    except:
        return [{'nombre': 'Mi Teléfono', 'ip': '192.168.100.47'}]

def guardar_dispositivos(dispositivos):
    try:
        with open(DEVICES_FILE, 'w') as f:
            json.dump(dispositivos, f, indent=2)
    except:
        pass

# ============================================================
#   FUNCIONES DE CIERRE
# ============================================================
def matar_scrcpy():
    try:
        subprocess.run('taskkill /f /im scrcpy.exe', shell=True, capture_output=True)
        print("✅ Scrcpy cerrado.")
        return True
    except:
        return False

def matar_adb():
    try:
        subprocess.run(f'{RUTA_ADB} kill-server', shell=True, capture_output=True)
        print("✅ ADB cerrado.")
        return True
    except Exception as e:
        print(f"❌ Error al cerrar ADB: {e}")
        return False

def cerrar_todo():
    try:
        matar_scrcpy()
        matar_adb()
        print("🧹 Todos los procesos cerrados correctamente.")
    except Exception as e:
        print(f"❌ Error al cerrar: {e}")

def manejar_senal(sig, frame):
    print("\n🛑 Recibida señal de cierre...")
    cerrar_todo()
    sys.exit(0)

atexit.register(cerrar_todo)
signal.signal(signal.SIGINT, manejar_senal)
signal.signal(signal.SIGTERM, manejar_senal)

# ============================================================
#   FUNCIONES PRINCIPALES
# ============================================================
def ejecutar_comando(comando):
    try:
        comando_modificado = comando.replace('adb', RUTA_ADB)
        resultado = subprocess.run(
            comando_modificado, 
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

def abrir_scrcpy_interno(ip=None):
    try:
        matar_scrcpy()
        opciones_completas = obtener_opciones_completas()
        
        if not os.path.exists(RUTA_SCRCPY):
            print(f"❌ No se encontró scrcpy en: {RUTA_SCRCPY}")
            return False
        
        # Si se proporciona IP, usar -s para dispositivo específico
        if ip:
            comando = f'start {RUTA_SCRCPY} -s {ip}:{PUERTO} {opciones_completas}'
        else:
            comando = f'start {RUTA_SCRCPY} {opciones_completas}'
        
        print(f"🔍 Ejecutando: {comando}")
        subprocess.Popen(comando, shell=True)
        print("✅ Scrcpy iniciado")
        return True
    except Exception as e:
        print(f"❌ Error al abrir scrcpy: {e}")
        return False

# ============================================================
#   FUNCIÓN PARA DESCONECTAR TODOS LOS DISPOSITIVOS
# ============================================================
def desconectar_todos():
    """Desconecta todos los dispositivos ADB"""
    try:
        resultado = ejecutar_comando('adb devices')
        lineas = resultado['stdout'].split('\n')
        
        for linea in lineas:
            if ':' in linea and 'device' in linea:
                ip_puerto = linea.split()[0].strip()
                if ip_puerto and ':' in ip_puerto:
                    ejecutar_comando(f'adb disconnect {ip_puerto}')
                    print(f"🔌 Desconectado: {ip_puerto}")
        
        return True
    except Exception as e:
        print(f"❌ Error al desconectar todos: {e}")
        return False

# ============================================================
#   RUTAS FRONTEND
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

# ============================================================
#   ENDPOINTS DE DISPOSITIVOS
# ============================================================
@app.route('/api/dispositivos', methods=['GET'])
def get_dispositivos():
    return jsonify({'dispositivos': obtener_dispositivos()})

@app.route('/api/dispositivos', methods=['POST'])
def agregar_dispositivo():
    try:
        data = request.json
        nombre = data.get('nombre', '')
        ip = data.get('ip', '')
        
        if not nombre or not ip:
            return jsonify({'error': 'Nombre e IP son requeridos'}), 400
        
        dispositivos = obtener_dispositivos()
        
        for d in dispositivos:
            if d['ip'] == ip:
                return jsonify({'error': 'Esta IP ya está registrada'}), 400
        
        dispositivos.append({'nombre': nombre, 'ip': ip})
        guardar_dispositivos(dispositivos)
        
        return jsonify({'success': True, 'dispositivos': dispositivos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dispositivos/<ip>', methods=['DELETE'])
def eliminar_dispositivo(ip):
    try:
        dispositivos = obtener_dispositivos()
        dispositivos = [d for d in dispositivos if d['ip'] != ip]
        guardar_dispositivos(dispositivos)
        return jsonify({'success': True, 'dispositivos': dispositivos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dispositivos/<ip>', methods=['PUT'])
def editar_dispositivo(ip):
    try:
        data = request.json
        nuevo_nombre = data.get('nombre', '')
        nueva_ip = data.get('ip', '')
        
        if not nuevo_nombre or not nueva_ip:
            return jsonify({'error': 'Nombre e IP son requeridos'}), 400
        
        dispositivos = obtener_dispositivos()
        
        for i, d in enumerate(dispositivos):
            if d['ip'] == ip:
                if nueva_ip != ip:
                    for otro in dispositivos:
                        if otro['ip'] == nueva_ip:
                            return jsonify({'error': 'Esta IP ya está registrada'}), 400
                dispositivos[i] = {'nombre': nuevo_nombre, 'ip': nueva_ip}
                guardar_dispositivos(dispositivos)
                return jsonify({'success': True, 'dispositivos': dispositivos})
        
        return jsonify({'error': 'Dispositivo no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dispositivos/seleccionar', methods=['POST'])
def seleccionar_dispositivo():
    try:
        data = request.json
        ip = data.get('ip', '')
        
        if not ip:
            return jsonify({'error': 'IP requerida'}), 400
        
        guardar_ip(ip)
        return jsonify({'success': True, 'ip': ip})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================
#   ENDPOINT CONEXIÓN MULTI-DISPOSITIVO
# ============================================================
@app.route('/api/conectar-dispositivo', methods=['POST'])
def conectar_dispositivo():
    """Conecta un dispositivo específico sin desconectar los demás"""
    try:
        data = request.json
        ip = data.get('ip', '')
        nombre = data.get('nombre', '')
        
        if not ip:
            return jsonify({'error': 'IP requerida'}), 400
        
        print(f"📡 Conectando a {ip}:{PUERTO}")
        resultado = ejecutar_comando(f'adb connect {ip}:{PUERTO}')
        
        print(f"📤 Salida: {resultado['stdout']}")
        print(f"📥 Error: {resultado['stderr']}")
        
        if resultado['success']:
            verificar = ejecutar_comando('adb devices')
            if ip in verificar['stdout']:
                opciones_completas = obtener_opciones_completas()
                comando = f'start {RUTA_SCRCPY} -s {ip}:{PUERTO} {opciones_completas}'
                subprocess.Popen(comando, shell=True)
                return jsonify({
                    'success': True, 
                    'message': f'✅ {nombre} conectado',
                    'ip': ip
                })
        
        return jsonify({'success': False, 'message': f'❌ No se pudo conectar {nombre}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ============================================================
#   OTROS ENDPOINTS
# ============================================================
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
    def cerrar():
        time.sleep(1)
        print("🛑 Navegador cerrado. Cerrando todo...")
        cerrar_todo()
        os._exit(0)
    
    threading.Thread(target=cerrar, daemon=True).start()
    return jsonify({'success': True, 'message': 'Cerrando servidor...'})

@app.route('/api/conectar', methods=['POST'])
def conectar():
    try:
        ip = obtener_ip_guardada()
        
        print("🔌 Desconectando todos los dispositivos...")
        desconectar_todos()
        
        time.sleep(1)
        
        print(f"📡 Conectando a {ip}:{PUERTO}")
        resultado = ejecutar_comando(f'adb connect {ip}:{PUERTO}')
        
        print(f"📤 Salida: {resultado['stdout']}")
        print(f"📥 Error: {resultado['stderr']}")
        
        if resultado['success']:
            verificar = ejecutar_comando('adb devices')
            if ip in verificar['stdout']:
                matar_scrcpy()
                abrir_scrcpy_interno(ip)
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
        matar_adb()
        return jsonify({'success': True, 'message': 'Desconectado y ADB cerrado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/abrir-scrcpy', methods=['POST'])
def abrir_scrcpy():
    try:
        ip = obtener_ip_guardada()
        if abrir_scrcpy_interno(ip):
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

@app.route('/api/dispositivos-adb', methods=['GET'])
def dispositivos_adb():
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
#   ABRIR NAVEGADOR
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
    print(f"  📁 Carpeta: {BASE_DIR}")
    print(f"  📁 Frontend: {FRONTEND_FOLDER}")
    print(f"  📁 Scrcpy: {RUTA_SCRCPY}")
    print(f"  📁 ADB: {RUTA_ADB}")
    print(f"  🌐 Abre tu navegador en: http://localhost:5000")
    print("=" * 60)
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"ERROR: {e}")
        input("Presiona Enter para salir...")