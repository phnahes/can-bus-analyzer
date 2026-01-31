"""
Internationalization (i18n) - Multi-language support for CAN Analyzer
"""

from typing import Dict, Optional


class I18n:
    """Internationalization manager"""
    
    # Available languages
    LANGUAGES = {
        'en': 'English',
        'pt': 'Português',
        'es': 'Español',
        'de': 'Deutsch',
        'fr': 'Français'
    }
    
    # Translation dictionary
    TRANSLATIONS = {
        # Application
        'app_title': {
            'en': 'CAN Analyzer - macOS',
            'pt': 'CAN Analyzer - macOS',
            'es': 'Analizador CAN - macOS',
            'de': 'CAN Analyzer - macOS',
            'fr': 'Analyseur CAN - macOS'
        },
        
        # Menu - File
        'menu_file': {
            'en': 'File',
            'pt': 'Arquivo',
            'es': 'Archivo',
            'de': 'Datei',
            'fr': 'Fichier'
        },
        'menu_connect': {
            'en': 'Connect',
            'pt': 'Conectar',
            'es': 'Conectar',
            'de': 'Verbinden',
            'fr': 'Connecter'
        },
        'menu_disconnect': {
            'en': 'Disconnect',
            'pt': 'Desconectar',
            'es': 'Desconectar',
            'de': 'Trennen',
            'fr': 'Déconnecter'
        },
        'menu_reset': {
            'en': 'Reset',
            'pt': 'Resetar',
            'es': 'Reiniciar',
            'de': 'Zurücksetzen',
            'fr': 'Réinitialiser'
        },
        'menu_save_rx_log': {
            'en': 'Save Receive Log',
            'pt': 'Salvar Log de Recepção',
            'es': 'Guardar Registro de Recepción',
            'de': 'Empfangsprotokoll speichern',
            'fr': 'Enregistrer le journal de réception'
        },
        'menu_load_rx_log': {
            'en': 'Load Receive Log',
            'pt': 'Carregar Log de Recepção',
            'es': 'Cargar Registro de Recepción',
            'de': 'Empfangsprotokoll laden',
            'fr': 'Charger le journal de réception'
        },
        'menu_save_tx_list': {
            'en': 'Save Transmit List',
            'pt': 'Salvar Lista de Transmissão',
            'es': 'Guardar Lista de Transmisión',
            'de': 'Sendeliste speichern',
            'fr': 'Enregistrer la liste de transmission'
        },
        'menu_load_tx_list': {
            'en': 'Load Transmit List',
            'pt': 'Carregar Lista de Transmissão',
            'es': 'Cargar Lista de Transmisión',
            'de': 'Sendeliste laden',
            'fr': 'Charger la liste de transmission'
        },
        'menu_exit': {
            'en': 'Exit',
            'pt': 'Sair',
            'es': 'Salir',
            'de': 'Beenden',
            'fr': 'Quitter'
        },
        
        # Menu - View
        'menu_view': {
            'en': 'View',
            'pt': 'Ver',
            'es': 'Ver',
            'de': 'Ansicht',
            'fr': 'Affichage'
        },
        'menu_tracer_mode': {
            'en': 'Tracer Mode',
            'pt': 'Modo Tracer',
            'es': 'Modo Rastreador',
            'de': 'Tracer-Modus',
            'fr': 'Mode traceur'
        },
        'menu_clear_receive': {
            'en': 'Clear Receive',
            'pt': 'Limpar Recepção',
            'es': 'Limpiar Recepción',
            'de': 'Empfang löschen',
            'fr': 'Effacer la réception'
        },
        
        # Menu - Tools
        'menu_tools': {
            'en': 'Tools',
            'pt': 'Ferramentas',
            'es': 'Herramientas',
            'de': 'Werkzeuge',
            'fr': 'Outils'
        },
        'menu_filters': {
            'en': 'Filters',
            'pt': 'Filtros',
            'es': 'Filtros',
            'de': 'Filter',
            'fr': 'Filtres'
        },
        'menu_triggers': {
            'en': 'Triggers',
            'pt': 'Triggers',
            'es': 'Disparadores',
            'de': 'Auslöser',
            'fr': 'Déclencheurs'
        },
        'menu_statistics': {
            'en': 'Statistics',
            'pt': 'Estatísticas',
            'es': 'Estadísticas',
            'de': 'Statistiken',
            'fr': 'Statistiques'
        },
        
        # Menu - Settings
        'menu_settings': {
            'en': 'Settings',
            'pt': 'Configurações',
            'es': 'Configuración',
            'de': 'Einstellungen',
            'fr': 'Paramètres'
        },
        'menu_connection_settings': {
            'en': 'Connection Settings',
            'pt': 'Configurações de Conexão',
            'es': 'Configuración de Conexión',
            'de': 'Verbindungseinstellungen',
            'fr': 'Paramètres de connexion'
        },
        'menu_language': {
            'en': 'Language',
            'pt': 'Idioma',
            'es': 'Idioma',
            'de': 'Sprache',
            'fr': 'Langue'
        },
        
        # Menu - Help
        'menu_help': {
            'en': 'Help',
            'pt': 'Ajuda',
            'es': 'Ayuda',
            'de': 'Hilfe',
            'fr': 'Aide'
        },
        'menu_about': {
            'en': 'About',
            'pt': 'Sobre',
            'es': 'Acerca de',
            'de': 'Über',
            'fr': 'À propos'
        },
        'about_title': {
            'en': 'CAN Analyzer for macOS',
            'pt': 'CAN Analyzer para macOS',
            'es': 'Analizador CAN para macOS',
            'de': 'CAN-Analysator für macOS',
            'fr': 'Analyseur CAN pour macOS'
        },
        'about_version': {
            'en': 'Version',
            'pt': 'Versão',
            'es': 'Versión',
            'de': 'Version',
            'fr': 'Version'
        },
        'about_description': {
            'en': 'Description',
            'pt': 'Descrição',
            'es': 'Descripción',
            'de': 'Beschreibung',
            'fr': 'Description'
        },
        'about_desc_text': {
            'en': 'Complete CAN bus analyzer',
            'pt': 'Analisador de barramento CAN completo',
            'es': 'Analizador de bus CAN completo',
            'de': 'Vollständiger CAN-Bus-Analysator',
            'fr': 'Analyseur de bus CAN complet'
        },
        'about_replicates': {
            'en': 'Replicates CANHacker functionalities for macOS',
            'pt': 'Replica funcionalidades do CANHacker para macOS',
            'es': 'Replica funcionalidades de CANHacker para macOS',
            'de': 'Repliziert CANHacker-Funktionen für macOS',
            'fr': 'Réplique les fonctionnalités de CANHacker pour macOS'
        },
        'about_features': {
            'en': 'Features',
            'pt': 'Funcionalidades',
            'es': 'Características',
            'de': 'Funktionen',
            'fr': 'Fonctionnalités'
        },
        'about_developed': {
            'en': 'Developed with',
            'pt': 'Desenvolvido com',
            'es': 'Desarrollado con',
            'de': 'Entwickelt mit',
            'fr': 'Développé avec'
        },
        'about_year': {
            'en': 'Year',
            'pt': 'Ano',
            'es': 'Año',
            'de': 'Jahr',
            'fr': 'Année'
        },
        
        # Buttons
        'btn_connect': {
            'en': 'Connect',
            'pt': 'Conectar',
            'es': 'Conectar',
            'de': 'Verbinden',
            'fr': 'Connecter'
        },
        'btn_disconnect': {
            'en': 'Disconnect',
            'pt': 'Desconectar',
            'es': 'Desconectar',
            'de': 'Trennen',
            'fr': 'Déconnecter'
        },
        'btn_reset': {
            'en': 'Reset',
            'pt': 'Resetar',
            'es': 'Reiniciar',
            'de': 'Zurücksetzen',
            'fr': 'Réinitialiser'
        },
        'btn_record': {
            'en': 'Record',
            'pt': 'Gravar',
            'es': 'Grabar',
            'de': 'Aufnehmen',
            'fr': 'Enregistrer'
        },
        'btn_pause': {
            'en': 'Pause',
            'pt': 'Pausar',
            'es': 'Pausar',
            'de': 'Pause',
            'fr': 'Pause'
        },
        'btn_clear': {
            'en': 'Clear',
            'pt': 'Limpar',
            'es': 'Limpiar',
            'de': 'Löschen',
            'fr': 'Effacer'
        },
        'btn_tracer': {
            'en': 'Tracer',
            'pt': 'Tracer',
            'es': 'Rastreador',
            'de': 'Tracer',
            'fr': 'Traceur'
        },
        'btn_monitor': {
            'en': 'Monitor',
            'pt': 'Monitor',
            'es': 'Monitor',
            'de': 'Monitor',
            'fr': 'Moniteur'
        },
        'btn_filters': {
            'en': 'Filters',
            'pt': 'Filtros',
            'es': 'Filtros',
            'de': 'Filter',
            'fr': 'Filtres'
        },
        'btn_add': {
            'en': 'Add',
            'pt': 'Adicionar',
            'es': 'Añadir',
            'de': 'Hinzufügen',
            'fr': 'Ajouter'
        },
        'btn_send': {
            'en': 'Send',
            'pt': 'Enviar',
            'es': 'Enviar',
            'de': 'Senden',
            'fr': 'Envoyer'
        },
        'btn_remove': {
            'en': 'Remove',
            'pt': 'Remover',
            'es': 'Eliminar',
            'de': 'Entfernen',
            'fr': 'Supprimer'
        },
        'btn_play_all': {
            'en': 'Play All',
            'pt': 'Reproduzir Tudo',
            'es': 'Reproducir Todo',
            'de': 'Alle abspielen',
            'fr': 'Tout lire'
        },
        'btn_play_selected': {
            'en': 'Play Selected',
            'pt': 'Reproduzir Selecionados',
            'es': 'Reproducir Seleccionados',
            'de': 'Ausgewählte abspielen',
            'fr': 'Lire la sélection'
        },
        'btn_stop': {
            'en': 'Stop',
            'pt': 'Parar',
            'es': 'Detener',
            'de': 'Stoppen',
            'fr': 'Arrêter'
        },
        'btn_save': {
            'en': 'Save',
            'pt': 'Salvar',
            'es': 'Guardar',
            'de': 'Speichern',
            'fr': 'Enregistrer'
        },
        'btn_load': {
            'en': 'Load',
            'pt': 'Carregar',
            'es': 'Cargar',
            'de': 'Laden',
            'fr': 'Charger'
        },
        'btn_ok': {
            'en': 'OK',
            'pt': 'OK',
            'es': 'OK',
            'de': 'OK',
            'fr': 'OK'
        },
        'btn_cancel': {
            'en': 'Cancel',
            'pt': 'Cancelar',
            'es': 'Cancelar',
            'de': 'Abbrechen',
            'fr': 'Annuler'
        },
        'btn_close': {
            'en': 'Close',
            'pt': 'Fechar',
            'es': 'Cerrar',
            'de': 'Schließen',
            'fr': 'Fermer'
        },
        'btn_single': {
            'en': 'Single Shot',
            'pt': 'Envio Único',
            'es': 'Envío Único',
            'de': 'Einzelschuss',
            'fr': 'Envoi unique'
        },
        'btn_copy': {
            'en': 'Copy',
            'pt': 'Copiar',
            'es': 'Copiar',
            'de': 'Kopieren',
            'fr': 'Copier'
        },
        'btn_send_all': {
            'en': 'Send All',
            'pt': 'Enviar Todos',
            'es': 'Enviar Todos',
            'de': 'Alle senden',
            'fr': 'Tout envoyer'
        },
        'btn_stop_all': {
            'en': 'Stop All',
            'pt': 'Parar Todos',
            'es': 'Detener Todos',
            'de': 'Alle stoppen',
            'fr': 'Tout arrêter'
        },
        'btn_delete': {
            'en': 'Delete',
            'pt': 'Excluir',
            'es': 'Eliminar',
            'de': 'Löschen',
            'fr': 'Supprimer'
        },
        'btn_refresh': {
            'en': 'Refresh',
            'pt': 'Atualizar',
            'es': 'Actualizar',
            'de': 'Aktualisieren',
            'fr': 'Actualiser'
        },
        'btn_select': {
            'en': 'Select',
            'pt': 'Selecionar',
            'es': 'Seleccionar',
            'de': 'Auswählen',
            'fr': 'Sélectionner'
        },
        'btn_scan_devices': {
            'en': 'Scan Devices',
            'pt': 'Buscar Dispositivos',
            'es': 'Buscar Dispositivos',
            'de': 'Geräte scannen',
            'fr': 'Scanner les appareils'
        },
        
        # Labels
        'label_receive': {
            'en': 'Receive (Monitor)',
            'pt': 'Recepção (Monitor)',
            'es': 'Recepción (Monitor)',
            'de': 'Empfang (Monitor)',
            'fr': 'Réception (Moniteur)'
        },
        'label_transmit': {
            'en': 'Transmit',
            'pt': 'Transmissão',
            'es': 'Transmisión',
            'de': 'Senden',
            'fr': 'Transmission'
        },
        'label_id': {
            'en': 'ID',
            'pt': 'ID',
            'es': 'ID',
            'de': 'ID',
            'fr': 'ID'
        },
        'label_dlc': {
            'en': 'DLC',
            'pt': 'DLC',
            'es': 'DLC',
            'de': 'DLC',
            'fr': 'DLC'
        },
        'label_data': {
            'en': 'Data',
            'pt': 'Dados',
            'es': 'Datos',
            'de': 'Daten',
            'fr': 'Données'
        },
        'label_period': {
            'en': 'Period',
            'pt': 'Período',
            'es': 'Período',
            'de': 'Periode',
            'fr': 'Période'
        },
        'label_count': {
            'en': 'Count',
            'pt': 'Contador',
            'es': 'Contador',
            'de': 'Zähler',
            'fr': 'Compteur'
        },
        'label_ascii': {
            'en': 'ASCII',
            'pt': 'ASCII',
            'es': 'ASCII',
            'de': 'ASCII',
            'fr': 'ASCII'
        },
        'label_comment': {
            'en': 'Comment',
            'pt': 'Comentário',
            'es': 'Comentario',
            'de': 'Kommentar',
            'fr': 'Commentaire'
        },
        'label_timestamp': {
            'en': 'Timestamp',
            'pt': 'Timestamp',
            'es': 'Marca de tiempo',
            'de': 'Zeitstempel',
            'fr': 'Horodatage'
        },
        'label_interval': {
            'en': 'Interval (ms)',
            'pt': 'Intervalo (ms)',
            'es': 'Intervalo (ms)',
            'de': 'Intervall (ms)',
            'fr': 'Intervalle (ms)'
        },
        'label_repeat': {
            'en': 'Repeat',
            'pt': 'Repetir',
            'es': 'Repetir',
            'de': 'Wiederholen',
            'fr': 'Répéter'
        },
        'label_active': {
            'en': 'Active',
            'pt': 'Ativo',
            'es': 'Activo',
            'de': 'Aktiv',
            'fr': 'Actif'
        },
        'label_device_name': {
            'en': 'Device Name',
            'pt': 'Nome do Dispositivo',
            'es': 'Nombre del Dispositivo',
            'de': 'Gerätename',
            'fr': 'Nom de l\'appareil'
        },
        'label_device_path': {
            'en': 'Device Path',
            'pt': 'Caminho do Dispositivo',
            'es': 'Ruta del Dispositivo',
            'de': 'Gerätepfad',
            'fr': 'Chemin de l\'appareil'
        },
        'label_device_description': {
            'en': 'Description',
            'pt': 'Descrição',
            'es': 'Descripción',
            'de': 'Beschreibung',
            'fr': 'Description'
        },
        'label_simulation_mode': {
            'en': 'Simulation Mode',
            'pt': 'Modo Simulação',
            'es': 'Modo Simulación',
            'de': 'Simulationsmodus',
            'fr': 'Mode Simulation'
        },
        'tooltip_simulation_mode': {
            'en': 'Enable to use simulated CAN data instead of real hardware',
            'pt': 'Ative para usar dados CAN simulados ao invés de hardware real',
            'es': 'Active para usar datos CAN simulados en lugar de hardware real',
            'de': 'Aktivieren Sie, um simulierte CAN-Daten anstelle echter Hardware zu verwenden',
            'fr': 'Activer pour utiliser des données CAN simulées au lieu du matériel réel'
        },
        
        # Status
        'status_connected': {
            'en': 'Connected',
            'pt': 'Conectado',
            'es': 'Conectado',
            'de': 'Verbunden',
            'fr': 'Connecté'
        },
        'status_disconnected': {
            'en': 'Disconnected',
            'pt': 'Desconectado',
            'es': 'Desconectado',
            'de': 'Getrennt',
            'fr': 'Déconnecté'
        },
        'status_recording': {
            'en': 'Recording',
            'pt': 'Gravando',
            'es': 'Grabando',
            'de': 'Aufnahme',
            'fr': 'Enregistrement'
        },
        'status_paused': {
            'en': 'Paused',
            'pt': 'Pausado',
            'es': 'Pausado',
            'de': 'Pausiert',
            'fr': 'En pause'
        },
        'status_listen_only': {
            'en': 'Listen Only Mode',
            'pt': 'Modo Apenas Leitura',
            'es': 'Modo Solo Escucha',
            'de': 'Nur-Lese-Modus',
            'fr': 'Mode écoute seule'
        },
        'status_normal': {
            'en': 'Normal Mode',
            'pt': 'Modo Normal',
            'es': 'Modo Normal',
            'de': 'Normalmodus',
            'fr': 'Mode normal'
        },
        'status_device': {
            'en': 'Device',
            'pt': 'Dispositivo',
            'es': 'Dispositivo',
            'de': 'Gerät',
            'fr': 'Appareil'
        },
        
        # Messages
        'msg_connecting': {
            'en': 'Connecting to CAN bus...',
            'pt': 'Conectando ao barramento CAN...',
            'es': 'Conectando al bus CAN...',
            'de': 'Verbindung zum CAN-Bus...',
            'fr': 'Connexion au bus CAN...'
        },
        'msg_connection_established': {
            'en': 'Connection established successfully',
            'pt': 'Conexão estabelecida com sucesso',
            'es': 'Conexión establecida con éxito',
            'de': 'Verbindung erfolgreich hergestellt',
            'fr': 'Connexion établie avec succès'
        },
        'msg_connection_error': {
            'en': 'Connection error',
            'pt': 'Erro na conexão',
            'es': 'Error de conexión',
            'de': 'Verbindungsfehler',
            'fr': 'Erreur de connexion'
        },
        'msg_disconnected': {
            'en': 'Disconnected from CAN bus',
            'pt': 'Desconectado do barramento CAN',
            'es': 'Desconectado del bus CAN',
            'de': 'Vom CAN-Bus getrennt',
            'fr': 'Déconnecté du bus CAN'
        },
        'msg_message_sent': {
            'en': 'Message sent',
            'pt': 'Mensagem enviada',
            'es': 'Mensaje enviado',
            'de': 'Nachricht gesendet',
            'fr': 'Message envoyé'
        },
        'msg_message_added': {
            'en': 'message(s) added to transmit list',
            'pt': 'mensagem(ns) adicionada(s) à lista de transmissão',
            'es': 'mensaje(s) añadido(s) a la lista de transmisión',
            'de': 'Nachricht(en) zur Sendeliste hinzugefügt',
            'fr': 'message(s) ajouté(s) à la liste de transmission'
        },
        'msg_log_saved': {
            'en': 'Log saved successfully',
            'pt': 'Log salvo com sucesso',
            'es': 'Registro guardado con éxito',
            'de': 'Protokoll erfolgreich gespeichert',
            'fr': 'Journal enregistré avec succès'
        },
        'msg_log_loaded': {
            'en': 'Log loaded successfully',
            'pt': 'Log carregado com sucesso',
            'es': 'Registro cargado con éxito',
            'de': 'Protokoll erfolgreich geladen',
            'fr': 'Journal chargé avec succès'
        },
        'msg_no_messages': {
            'en': 'No messages to save',
            'pt': 'Nenhuma mensagem para salvar',
            'es': 'No hay mensajes para guardar',
            'de': 'Keine Nachrichten zu speichern',
            'fr': 'Aucun message à enregistrer'
        },
        'msg_select_message': {
            'en': 'Please select a message',
            'pt': 'Por favor selecione uma mensagem',
            'es': 'Por favor seleccione un mensaje',
            'de': 'Bitte wählen Sie eine Nachricht',
            'fr': 'Veuillez sélectionner un message'
        },
        'msg_settings_updated': {
            'en': 'Settings updated!',
            'pt': 'Configurações atualizadas!',
            'es': '¡Configuración actualizada!',
            'de': 'Einstellungen aktualisiert!',
            'fr': 'Paramètres mis à jour!'
        },
        'msg_simulation_mode': {
            'en': 'Connecting in simulation mode (USB CAN adapter not available)',
            'pt': 'Conectando em modo simulação (adaptador USB CAN não disponível)',
            'es': 'Conectando en modo simulación (adaptador USB CAN no disponible)',
            'de': 'Verbindung im Simulationsmodus (USB-CAN-Adapter nicht verfügbar)',
            'fr': 'Connexion en mode simulation (adaptateur USB CAN non disponible)'
        },
        'msg_device_connected': {
            'en': 'USB device connected: {device}',
            'pt': 'Dispositivo USB conectado: {device}',
            'es': 'Dispositivo USB conectado: {device}',
            'de': 'USB-Gerät verbunden: {device}',
            'fr': 'Appareil USB connecté: {device}'
        },
        'msg_device_disconnected': {
            'en': 'USB device disconnected: {device}',
            'pt': 'Dispositivo USB desconectado: {device}',
            'es': 'Dispositivo USB desconectado: {device}',
            'de': 'USB-Gerät getrennt: {device}',
            'fr': 'Appareil USB déconnecté: {device}'
        },
        'msg_usb_monitor_not_available': {
            'en': 'USB device monitor not available',
            'pt': 'Monitor de dispositivos USB não disponível',
            'es': 'Monitor de dispositivos USB no disponible',
            'de': 'USB-Gerätemonitor nicht verfügbar',
            'fr': 'Moniteur de périphériques USB non disponible'
        },
        'msg_no_usb_devices_found': {
            'en': 'No USB devices found. Connect a device and click Refresh.',
            'pt': 'Nenhum dispositivo USB encontrado. Conecte um dispositivo e clique em Atualizar.',
            'es': 'No se encontraron dispositivos USB. Conecte un dispositivo y haga clic en Actualizar.',
            'de': 'Keine USB-Geräte gefunden. Schließen Sie ein Gerät an und klicken Sie auf Aktualisieren.',
            'fr': 'Aucun appareil USB trouvé. Connectez un appareil et cliquez sur Actualiser.'
        },
        'msg_usb_devices_found': {
            'en': '{count} device(s) found',
            'pt': '{count} dispositivo(s) encontrado(s)',
            'es': '{count} dispositivo(s) encontrado(s)',
            'de': '{count} Gerät(e) gefunden',
            'fr': '{count} appareil(s) trouvé(s)'
        },
        'msg_select_device': {
            'en': 'Please select a device',
            'pt': 'Por favor selecione um dispositivo',
            'es': 'Por favor seleccione un dispositivo',
            'de': 'Bitte wählen Sie ein Gerät',
            'fr': 'Veuillez sélectionner un appareil'
        },
        'msg_device_in_use': {
            'en': 'Cannot disconnect: device is currently in use',
            'pt': 'Não é possível desconectar: dispositivo está em uso',
            'es': 'No se puede desconectar: el dispositivo está en uso',
            'de': 'Trennung nicht möglich: Gerät wird verwendet',
            'fr': 'Impossible de déconnecter: l\'appareil est en cours d\'utilisation'
        },
        
        # Context Menu
        'ctx_add_to_transmit': {
            'en': 'Add to Transmit List',
            'pt': 'Adicionar à Lista de Transmissão',
            'es': 'Añadir a Lista de Transmisión',
            'de': 'Zur Sendeliste hinzufügen',
            'fr': 'Ajouter à la liste de transmission'
        },
        'ctx_copy_id': {
            'en': 'Copy ID',
            'pt': 'Copiar ID',
            'es': 'Copiar ID',
            'de': 'ID kopieren',
            'fr': 'Copier l\'ID'
        },
        'ctx_copy_data': {
            'en': 'Copy Data',
            'pt': 'Copiar Dados',
            'es': 'Copiar Datos',
            'de': 'Daten kopieren',
            'fr': 'Copier les données'
        },
        'ctx_bit_field_viewer': {
            'en': 'Bit Field Viewer',
            'pt': 'Visualizador de Bits',
            'es': 'Visor de Campo de Bits',
            'de': 'Bitfeld-Viewer',
            'fr': 'Visualiseur de champ de bits'
        },
        
        # Dialogs
        'dialog_about_title': {
            'en': 'About CAN Analyzer',
            'pt': 'Sobre CAN Analyzer',
            'es': 'Acerca de CAN Analyzer',
            'de': 'Über CAN Analyzer',
            'fr': 'À propos de CAN Analyzer'
        },
        'dialog_about_text': {
            'en': 'CAN Analyzer for macOS\n\nVersion 1.0\n\nCAN bus analysis tool with CANHacker-like functionality',
            'pt': 'CAN Analyzer para macOS\n\nVersão 1.0\n\nFerramenta de análise de barramento CAN com funcionalidades similares ao CANHacker',
            'es': 'CAN Analyzer para macOS\n\nVersión 1.0\n\nHerramienta de análisis de bus CAN con funcionalidad similar a CANHacker',
            'de': 'CAN Analyzer für macOS\n\nVersion 1.0\n\nCAN-Bus-Analysetool mit CANHacker-ähnlicher Funktionalität',
            'fr': 'CAN Analyzer pour macOS\n\nVersion 1.0\n\nOutil d\'analyse de bus CAN avec des fonctionnalités similaires à CANHacker'
        },
        'dialog_usb_device_title': {
            'en': 'Select USB Device',
            'pt': 'Selecionar Dispositivo USB',
            'es': 'Seleccionar Dispositivo USB',
            'de': 'USB-Gerät auswählen',
            'fr': 'Sélectionner un appareil USB'
        },
        'dialog_usb_device_info': {
            'en': 'Select a USB/Serial device to use for CAN communication. The list shows all available devices detected on your system.',
            'pt': 'Selecione um dispositivo USB/Serial para usar na comunicação CAN. A lista mostra todos os dispositivos disponíveis detectados no seu sistema.',
            'es': 'Seleccione un dispositivo USB/Serial para usar en la comunicación CAN. La lista muestra todos los dispositivos disponibles detectados en su sistema.',
            'de': 'Wählen Sie ein USB/Serielles Gerät für die CAN-Kommunikation. Die Liste zeigt alle verfügbaren Geräte auf Ihrem System.',
            'fr': 'Sélectionnez un périphérique USB/Série pour la communication CAN. La liste affiche tous les périphériques disponibles détectés sur votre système.'
        },
        'warning': {
            'en': 'Warning',
            'pt': 'Aviso',
            'es': 'Advertencia',
            'de': 'Warnung',
            'fr': 'Avertissement'
        },
    }
    
    def __init__(self, language: str = 'en'):
        """
        Initialize i18n manager
        
        Args:
            language: Language code (en, pt, es, de, fr)
        """
        self.current_language = language if language in self.LANGUAGES else 'en'
    
    def t(self, key: str, **kwargs) -> str:
        """
        Translate a key to the current language
        
        Args:
            key: Translation key
            **kwargs: Format arguments for the translation string
        
        Returns:
            Translated string
        """
        if key not in self.TRANSLATIONS:
            return f"[{key}]"  # Return key if not found
        
        translation = self.TRANSLATIONS[key].get(self.current_language)
        
        if translation is None:
            # Fallback to English
            translation = self.TRANSLATIONS[key].get('en', f"[{key}]")
        
        # Apply formatting if kwargs provided
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except KeyError:
                pass
        
        return translation
    
    def set_language(self, language: str):
        """
        Set the current language
        
        Args:
            language: Language code
        """
        if language in self.LANGUAGES:
            self.current_language = language
    
    def get_language(self) -> str:
        """Get the current language code"""
        return self.current_language
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get dictionary of available languages"""
        return self.LANGUAGES.copy()


# Global i18n instance
_i18n_instance: Optional[I18n] = None


def get_i18n() -> I18n:
    """Get the global i18n instance"""
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18n('en')  # Default to English
    return _i18n_instance


def init_i18n(language: str = 'en') -> I18n:
    """
    Initialize the global i18n instance
    
    Args:
        language: Initial language code
    
    Returns:
        I18n instance
    """
    global _i18n_instance
    _i18n_instance = I18n(language)
    return _i18n_instance


def t(key: str, **kwargs) -> str:
    """
    Shorthand function to translate a key
    
    Args:
        key: Translation key
        **kwargs: Format arguments
    
    Returns:
        Translated string
    """
    return get_i18n().t(key, **kwargs)
