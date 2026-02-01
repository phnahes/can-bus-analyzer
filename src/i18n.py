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
        # Application (window title uses app_title + " - " + platform at runtime)
        'app_title': {
            'en': 'CAN Analyzer',
            'pt': 'CAN Analyzer',
            'es': 'Analizador CAN',
            'de': 'CAN Analyzer',
            'fr': 'Analyseur CAN'
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
            'en': 'CAN Analyzer for {platform}',
            'pt': 'CAN Analyzer para {platform}',
            'es': 'Analizador CAN para {platform}',
            'de': 'CAN-Analysator für {platform}',
            'fr': 'Analyseur CAN pour {platform}'
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
            'en': 'Replicates CANHacker functionalities for {platform}',
            'pt': 'Replica funcionalidades do CANHacker para {platform}',
            'es': 'Replica funcionalidades de CANHacker para {platform}',
            'de': 'Repliziert CANHacker-Funktionen für {platform}',
            'fr': 'Réplique les fonctionnalités de CANHacker pour {platform}'
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
        
        # Table columns
        'col_channel': {
            'en': 'Channel',
            'pt': 'Canal',
            'es': 'Canal',
            'de': 'Kanal',
            'fr': 'Canal'
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
        
        # Notification messages
        'notif_connected': {
            'en': '✅ Connected successfully: {channel} @ {baudrate} kbit/s',
            'pt': '✅ Conectado com sucesso: {channel} @ {baudrate} kbit/s',
            'es': '✅ Conectado exitosamente: {channel} @ {baudrate} kbit/s',
            'de': '✅ Erfolgreich verbunden: {channel} @ {baudrate} kbit/s',
            'fr': '✅ Connecté avec succès: {channel} @ {baudrate} kbit/s'
        },
        'notif_simulation_mode': {
            'en': '⚠️ Simulation mode activated: {baudrate} kbit/s',
            'pt': '⚠️ Modo simulação ativado: {baudrate} kbit/s',
            'es': '⚠️ Modo simulación activado: {baudrate} kbit/s',
            'de': '⚠️ Simulationsmodus aktiviert: {baudrate} kbit/s',
            'fr': '⚠️ Mode simulation activé: {baudrate} kbit/s'
        },
        'notif_disconnected': {
            'en': '⏹ Disconnected',
            'pt': '⏹ Desconectado',
            'es': '⏹ Desconectado',
            'de': '⏹ Getrennt',
            'fr': '⏹ Déconnecté'
        },
        'notif_reset': {
            'en': 'Complete reset - data cleared, connection maintained',
            'pt': 'Reset completo - dados limpos, conexão mantida',
            'es': 'Reinicio completo - datos borrados, conexión mantenida',
            'de': 'Vollständiger Reset - Daten gelöscht, Verbindung beibehalten',
            'fr': 'Réinitialisation complète - données effacées, connexion maintenue'
        },
        'notif_recording_started': {
            'en': '⏺ Recording started - messages will be saved for playback',
            'pt': '⏺ Gravação iniciada - mensagens serão salvas para reprodução',
            'es': '⏺ Grabación iniciada - mensajes se guardarán para reproducción',
            'de': '⏺ Aufnahme gestartet - Nachrichten werden für Wiedergabe gespeichert',
            'fr': '⏺ Enregistrement démarré - messages seront sauvegardés pour lecture'
        },
        'notif_recording_stopped': {
            'en': '⏹ Recording stopped - {count} messages recorded and visible',
            'pt': '⏹ Gravação parada - {count} mensagens gravadas e visíveis',
            'es': '⏹ Grabación detenida - {count} mensajes grabados y visibles',
            'de': '⏹ Aufnahme gestoppt - {count} Nachrichten aufgenommen und sichtbar',
            'fr': '⏹ Enregistrement arrêté - {count} messages enregistrés et visibles'
        },
        'notif_recording_stopped_empty': {
            'en': '⏹ Recording stopped - no messages recorded',
            'pt': '⏹ Gravação parada - nenhuma mensagem gravada',
            'es': '⏹ Grabación detenida - ningún mensaje grabado',
            'de': '⏹ Aufnahme gestoppt - keine Nachrichten aufgenommen',
            'fr': '⏹ Enregistrement arrêté - aucun message enregistré'
        },
        'notif_tx_panel_visible': {
            'en': 'Transmit panel visible',
            'pt': 'Painel de Transmissão visível',
            'es': 'Panel de transmisión visible',
            'de': 'Sendepanel sichtbar',
            'fr': 'Panneau de transmission visible'
        },
        'notif_tx_panel_hidden': {
            'en': 'Transmit panel hidden',
            'pt': 'Painel de Transmissão ocultado',
            'es': 'Panel de transmisión oculto',
            'de': 'Sendepanel ausgeblendet',
            'fr': 'Panneau de transmission masqué'
        },
        'notif_recorded_cleared': {
            'en': 'Recorded messages cleared',
            'pt': 'Mensagens gravadas limpas',
            'es': 'Mensajes grabados borrados',
            'de': 'Aufgenommene Nachrichten gelöscht',
            'fr': 'Messages enregistrés effacés'
        },
        'notif_message_sent': {
            'en': '✅ Sent: 0x{id:03X}',
            'pt': '✅ Enviado: 0x{id:03X}',
            'es': '✅ Enviado: 0x{id:03X}',
            'de': '✅ Gesendet: 0x{id:03X}',
            'fr': '✅ Envoyé: 0x{id:03X}'
        },
        'notif_simulation_sent': {
            'en': '⚠️ Simulation mode: 0x{id:03X}',
            'pt': '⚠️ Modo simulação: 0x{id:03X}',
            'es': '⚠️ Modo simulación: 0x{id:03X}',
            'de': '⚠️ Simulationsmodus: 0x{id:03X}',
            'fr': '⚠️ Mode simulation: 0x{id:03X}'
        },
        'notif_error': {
            'en': '❌ Error: {error}',
            'pt': '❌ Erro: {error}',
            'es': '❌ Error: {error}',
            'de': '❌ Fehler: {error}',
            'fr': '❌ Erreur: {error}'
        },
        'notif_connect_first': {
            'en': '⚠️ Connect to CAN bus first!',
            'pt': '⚠️ Conecte-se ao barramento CAN primeiro!',
            'es': '⚠️ ¡Conéctese al bus CAN primero!',
            'de': '⚠️ Zuerst mit CAN-Bus verbinden!',
            'fr': '⚠️ Connectez-vous au bus CAN d\'abord!'
        },
        'notif_periodic_already_active': {
            'en': '⚠️ Periodic send already active!',
            'pt': '⚠️ Envio periódico já está ativo!',
            'es': '⚠️ ¡Envío periódico ya activo!',
            'de': '⚠️ Periodisches Senden bereits aktiv!',
            'fr': '⚠️ Envoi périodique déjà actif!'
        },
        'notif_no_messages_in_table': {
            'en': '⚠️ No messages in transmit table!',
            'pt': '⚠️ Nenhuma mensagem na tabela de transmissão!',
            'es': '⚠️ ¡No hay mensajes en la tabla de transmisión!',
            'de': '⚠️ Keine Nachrichten in der Sendetabelle!',
            'fr': '⚠️ Aucun message dans la table de transmission!'
        },
        'notif_periodic_started': {
            'en': '✅ Periodic send started: {count} message(s)',
            'pt': '✅ Envio periódico iniciado: {count} mensagem(ns)',
            'es': '✅ Envío periódico iniciado: {count} mensaje(s)',
            'de': '✅ Periodisches Senden gestartet: {count} Nachricht(en)',
            'fr': '✅ Envoi périodique démarré: {count} message(s)'
        },
        'notif_no_valid_period': {
            'en': '⚠️ No messages with valid period!',
            'pt': '⚠️ Nenhuma mensagem com período válido!',
            'es': '⚠️ ¡No hay mensajes con período válido!',
            'de': '⚠️ Keine Nachrichten mit gültiger Periode!',
            'fr': '⚠️ Aucun message avec période valide!'
        },
        'notif_no_periodic_active': {
            'en': '⚠️ No periodic send active!',
            'pt': '⚠️ Nenhum envio periódico ativo!',
            'es': '⚠️ ¡No hay envío periódico activo!',
            'de': '⚠️ Kein periodisches Senden aktiv!',
            'fr': '⚠️ Aucun envoi périodique actif!'
        },
        'notif_periodic_stopped': {
            'en': '⏹ Periodic send stopped',
            'pt': '⏹ Envio periódico parado',
            'es': '⏹ Envío periódico detenido',
            'de': '⏹ Periodisches Senden gestoppt',
            'fr': '⏹ Envoi périodique arrêté'
        },
        'notif_language_changed': {
            'en': 'Language changed to {language}',
            'pt': 'Idioma alterado para {language}',
            'es': 'Idioma cambiado a {language}',
            'de': 'Sprache geändert zu {language}',
            'fr': 'Langue changée en {language}'
        },
        'notif_log_saved': {
            'en': '✅ Log saved: {filename} ({count} messages)',
            'pt': '✅ Log salvo: {filename} ({count} mensagens)',
            'es': '✅ Log guardado: {filename} ({count} mensajes)',
            'de': '✅ Log gespeichert: {filename} ({count} Nachrichten)',
            'fr': '✅ Log sauvegardé: {filename} ({count} messages)'
        },
        'notif_log_loaded': {
            'en': '✅ Log loaded: {filename} ({count} messages)',
            'pt': '✅ Log carregado: {filename} ({count} mensagens)',
            'es': '✅ Log cargado: {filename} ({count} mensajes)',
            'de': '✅ Log geladen: {filename} ({count} Nachrichten)',
            'fr': '✅ Log chargé: {filename} ({count} messages)'
        },
        'notif_monitor_saved': {
            'en': '✅ Monitor saved: {filename} ({count} messages)',
            'pt': '✅ Monitor salvo: {filename} ({count} mensagens)',
            'es': '✅ Monitor guardado: {filename} ({count} mensajes)',
            'de': '✅ Monitor gespeichert: {filename} ({count} Nachrichten)',
            'fr': '✅ Moniteur sauvegardé: {filename} ({count} messages)'
        },
        'notif_monitor_loaded': {
            'en': '✅ Monitor loaded: {filename} ({count} messages)',
            'pt': '✅ Monitor carregado: {filename} ({count} mensagens)',
            'es': '✅ Monitor cargado: {filename} ({count} mensajes)',
            'de': '✅ Monitor geladen: {filename} ({count} Nachrichten)',
            'fr': '✅ Moniteur chargé: {filename} ({count} messages)'
        },
        'notif_tx_saved': {
            'en': '✅ TX saved: {filename} ({count} messages)',
            'pt': '✅ TX salvo: {filename} ({count} mensagens)',
            'es': '✅ TX guardado: {filename} ({count} mensajes)',
            'de': '✅ TX gespeichert: {filename} ({count} Nachrichten)',
            'fr': '✅ TX sauvegardé: {filename} ({count} messages)'
        },
        'notif_tx_loaded': {
            'en': '✅ TX loaded: {filename} ({count} messages)',
            'pt': '✅ TX carregado: {filename} ({count} mensagens)',
            'es': '✅ TX cargado: {filename} ({count} mensajes)',
            'de': '✅ TX geladen: {filename} ({count} Nachrichten)',
            'fr': '✅ TX chargé: {filename} ({count} messages)'
        },
        'notif_messages_sent': {
            'en': '✅ {count} message(s) sent',
            'pt': '✅ {count} mensagem(ns) enviada(s)',
            'es': '✅ {count} mensaje(s) enviado(s)',
            'de': '✅ {count} Nachricht(en) gesendet',
            'fr': '✅ {count} message(s) envoyé(s)'
        },
        'notif_periodic_stopped_count': {
            'en': '⏹ Periodic send stopped: {count} message(s)',
            'pt': '⏹ Envio periódico parado: {count} mensagem(ns)',
            'es': '⏹ Envío periódico detenido: {count} mensaje(s)',
            'de': '⏹ Periodisches Senden gestoppt: {count} Nachricht(en)',
            'fr': '⏹ Envoi périodique arrêté: {count} message(s)'
        },
        'notif_messages_deleted': {
            'en': '{count} message(s) deleted',
            'pt': '{count} mensagem(ns) deletada(s)',
            'es': '{count} mensaje(s) eliminado(s)',
            'de': '{count} Nachricht(en) gelöscht',
            'fr': '{count} message(s) supprimé(s)'
        },
        'notif_id_copied': {
            'en': 'ID copied: {id}',
            'pt': 'ID copiado: {id}',
            'es': 'ID copiado: {id}',
            'de': 'ID kopiert: {id}',
            'fr': 'ID copié: {id}'
        },
        'notif_data_copied': {
            'en': 'Data copied: {data}',
            'pt': 'Data copiado: {data}',
            'es': 'Datos copiados: {data}',
            'de': 'Daten kopiert: {data}',
            'fr': 'Données copiées: {data}'
        },
        'notif_playback_paused': {
            'en': '⏸ Playback paused',
            'pt': '⏸ Reprodução pausada',
            'es': '⏸ Reproducción pausada',
            'de': '⏸ Wiedergabe pausiert',
            'fr': '⏸ Lecture en pause'
        },
        'notif_playback_resumed': {
            'en': '▶ Playback resumed',
            'pt': '▶ Reprodução continuada',
            'es': '▶ Reproducción reanudada',
            'de': '▶ Wiedergabe fortgesetzt',
            'fr': '▶ Lecture reprise'
        },
        'notif_playback_playing': {
            'en': '▶ Playing {count} recorded messages...',
            'pt': '▶ Reproduzindo {count} mensagens gravadas...',
            'es': '▶ Reproduciendo {count} mensajes grabados...',
            'de': '▶ Wiedergabe von {count} aufgenommenen Nachrichten...',
            'fr': '▶ Lecture de {count} messages enregistrés...'
        },
        'notif_playback_stopped': {
            'en': '⏹ Playback stopped',
            'pt': '⏹ Reprodução parada',
            'es': '⏹ Reproducción detenida',
            'de': '⏹ Wiedergabe gestoppt',
            'fr': '⏹ Lecture arrêtée'
        },
        'notif_filters_enabled': {
            'en': 'Filters enabled: {count} ID(s)',
            'pt': 'Filtros ativados: {count} ID(s)',
            'es': 'Filtros activados: {count} ID(s)',
            'de': 'Filter aktiviert: {count} ID(s)',
            'fr': 'Filtres activés: {count} ID(s)'
        },
        'notif_filters_disabled': {
            'en': 'Filters disabled',
            'pt': 'Filtros desativados',
            'es': 'Filtros desactivados',
            'de': 'Filter deaktiviert',
            'fr': 'Filtres désactivés'
        },
        'notif_triggers_disabled': {
            'en': 'Triggers disabled',
            'pt': 'Triggers desativados',
            'es': 'Triggers desactivados',
            'de': 'Trigger deaktiviert',
            'fr': 'Déclencheurs désactivés'
        },
        
        # Theme settings
        'theme_group': {
            'en': 'Theme',
            'pt': 'Tema',
            'es': 'Tema',
            'de': 'Thema',
            'fr': 'Thème'
        },
        'theme_system': {
            'en': 'System',
            'pt': 'Sistema',
            'es': 'Sistema',
            'de': 'System',
            'fr': 'Système'
        },
        'theme_light': {
            'en': 'Light',
            'pt': 'Claro',
            'es': 'Claro',
            'de': 'Hell',
            'fr': 'Clair'
        },
        'theme_dark': {
            'en': 'Dark',
            'pt': 'Escuro',
            'es': 'Oscuro',
            'de': 'Dunkel',
            'fr': 'Sombre'
        },
        'theme_restart_info': {
            'en': 'Theme will be applied on next restart',
            'pt': 'Tema será aplicado no próximo reinício',
            'es': 'El tema se aplicará en el próximo reinicio',
            'de': 'Theme wird beim nächsten Neustart angewendet',
            'fr': 'Le thème sera appliqué au prochain redémarrage'
        },
        'msg_theme_applied': {
            'en': 'Theme applied successfully!',
            'pt': 'Tema aplicado com sucesso!',
            'es': '¡Tema aplicado con éxito!',
            'de': 'Theme erfolgreich angewendet!',
            'fr': 'Thème appliqué avec succès!'
        },
        'msg_language_applied': {
            'en': 'Language changed successfully!',
            'pt': 'Idioma alterado com sucesso!',
            'es': '¡Idioma cambiado con éxito!',
            'de': 'Sprache erfolgreich geändert!',
            'fr': 'Langue modifiée avec succès!'
        },
        'msg_language_and_theme_applied': {
            'en': 'Language and theme applied successfully!',
            'pt': 'Idioma e tema aplicados com sucesso!',
            'es': '¡Idioma y tema aplicados con éxito!',
            'de': 'Sprache und Theme erfolgreich angewendet!',
            'fr': 'Langue et thème appliqués avec succès!'
        },
        'msg_settings_saved': {
            'en': 'Settings saved successfully!',
            'pt': 'Configurações salvas com sucesso!',
            'es': '¡Configuración guardada con éxito!',
            'de': 'Einstellungen erfolgreich gespeichert!',
            'fr': 'Paramètres enregistrés avec succès!'
        },
        
        # Multi-CAN settings
        'multican_group': {
            'en': 'Multi-CAN Configuration',
            'pt': 'Configuração Multi-CAN',
            'es': 'Configuración Multi-CAN',
            'de': 'Multi-CAN-Konfiguration',
            'fr': 'Configuration Multi-CAN'
        },
        'multican_name': {
            'en': 'Name',
            'pt': 'Nome',
            'es': 'Nombre',
            'de': 'Name',
            'fr': 'Nom'
        },
        'multican_device': {
            'en': 'Device',
            'pt': 'Dispositivo',
            'es': 'Dispositivo',
            'de': 'Gerät',
            'fr': 'Appareil'
        },
        'multican_baudrate': {
            'en': 'Baudrate',
            'pt': 'Baudrate',
            'es': 'Baudrate',
            'de': 'Baudrate',
            'fr': 'Baudrate'
        },
        'multican_interface': {
            'en': 'Interface',
            'pt': 'Interface',
            'es': 'Interfaz',
            'de': 'Schnittstelle',
            'fr': 'Interface'
        },
        'multican_listen_only': {
            'en': 'Listen Only',
            'pt': 'Apenas Escuta',
            'es': 'Solo Escucha',
            'de': 'Nur Zuhören',
            'fr': 'Écoute Seulement'
        },
        'btn_add_can': {
            'en': 'Add CAN',
            'pt': 'Adicionar CAN',
            'es': 'Agregar CAN',
            'de': 'CAN hinzufügen',
            'fr': 'Ajouter CAN'
        },
        'btn_remove_can': {
            'en': 'Remove',
            'pt': 'Remover',
            'es': 'Eliminar',
            'de': 'Entfernen',
            'fr': 'Supprimer'
        },
        'multican_info': {
            'en': 'Configure multiple CAN buses. At least one bus is required.',
            'pt': 'Configure múltiplos barramentos CAN. Pelo menos um barramento é necessário.',
            'es': 'Configure múltiples buses CAN. Se requiere al menos un bus.',
            'de': 'Konfigurieren Sie mehrere CAN-Busse. Mindestens ein Bus ist erforderlich.',
            'fr': 'Configurez plusieurs bus CAN. Au moins un bus est requis.'
        },
        
        # Gateway
        'gateway_title': {
            'en': 'CAN Gateway Configuration',
            'pt': 'Configuração do Gateway CAN',
            'es': 'Configuración del Gateway CAN',
            'de': 'CAN Gateway Konfiguration',
            'fr': 'Configuration du Gateway CAN'
        },
        'gateway_transmission': {
            'en': 'Transmission Control',
            'pt': 'Controle de Transmissão',
            'es': 'Control de Transmisión',
            'de': 'Übertragungssteuerung',
            'fr': 'Contrôle de Transmission'
        },
        'gateway_enable': {
            'en': 'Enable Gateway',
            'pt': 'Ativar Gateway',
            'es': 'Activar Gateway',
            'de': 'Gateway aktivieren',
            'fr': 'Activer Gateway'
        },
        'gateway_transmit_from': {
            'en': 'Transmit from',
            'pt': 'Transmitir de',
            'es': 'Transmitir desde',
            'de': 'Übertragen von',
            'fr': 'Transmettre de'
        },
        'gateway_to': {
            'en': 'to',
            'pt': 'para',
            'es': 'a',
            'de': 'zu',
            'fr': 'à'
        },
        'gateway_blocking': {
            'en': 'Static Blocking Rules',
            'pt': 'Regras de Bloqueio Estático',
            'es': 'Reglas de Bloqueo Estático',
            'de': 'Statische Sperrregeln',
            'fr': 'Règles de Blocage Statique'
        },
        'gateway_channel': {
            'en': 'Channel',
            'pt': 'Canal',
            'es': 'Canal',
            'de': 'Kanal',
            'fr': 'Canal'
        },
        'gateway_id': {
            'en': 'ID',
            'pt': 'ID',
            'es': 'ID',
            'de': 'ID',
            'fr': 'ID'
        },
        'gateway_lock': {
            'en': 'Lock',
            'pt': 'Bloquear',
            'es': 'Bloquear',
            'de': 'Sperren',
            'fr': 'Bloquer'
        },
        'gateway_unlock': {
            'en': 'Unlock',
            'pt': 'Desbloquear',
            'es': 'Desbloquear',
            'de': 'Entsperren',
            'fr': 'Débloquer'
        },
        'gateway_enabled': {
            'en': 'Enabled',
            'pt': 'Ativado',
            'es': 'Activado',
            'de': 'Aktiviert',
            'fr': 'Activé'
        },
        'gateway_dynamic_blocking': {
            'en': 'Dynamic Blocking',
            'pt': 'Bloqueio Dinâmico',
            'es': 'Bloqueo Dinámico',
            'de': 'Dynamische Sperrung',
            'fr': 'Blocage Dynamique'
        },
        'gateway_id_from': {
            'en': 'ID From',
            'pt': 'ID De',
            'es': 'ID Desde',
            'de': 'ID Von',
            'fr': 'ID De'
        },
        'gateway_id_to': {
            'en': 'ID To',
            'pt': 'ID Até',
            'es': 'ID Hasta',
            'de': 'ID Bis',
            'fr': 'ID À'
        },
        'gateway_period': {
            'en': 'Period',
            'pt': 'Período',
            'es': 'Período',
            'de': 'Periode',
            'fr': 'Période'
        },
        'gateway_start': {
            'en': 'Start',
            'pt': 'Iniciar',
            'es': 'Iniciar',
            'de': 'Starten',
            'fr': 'Démarrer'
        },
        'gateway_stop': {
            'en': 'Stop',
            'pt': 'Parar',
            'es': 'Detener',
            'de': 'Stoppen',
            'fr': 'Arrêter'
        },
        'gateway_statistics': {
            'en': 'Statistics',
            'pt': 'Estatísticas',
            'es': 'Estadísticas',
            'de': 'Statistiken',
            'fr': 'Statistiques'
        },
        'gateway_stats_template': {
            'en': 'Forwarded: {forwarded} | Blocked: {blocked} | Modified: {modified}',
            'pt': 'Encaminhadas: {forwarded} | Bloqueadas: {blocked} | Modificadas: {modified}',
            'es': 'Reenviadas: {forwarded} | Bloqueadas: {blocked} | Modificadas: {modified}',
            'de': 'Weitergeleitet: {forwarded} | Blockiert: {blocked} | Modifiziert: {modified}',
            'fr': 'Transmis: {forwarded} | Bloqués: {blocked} | Modifiés: {modified}'
        },
        'gateway_reset_stats': {
            'en': 'Reset Statistics',
            'pt': 'Resetar Estatísticas',
            'es': 'Restablecer Estadísticas',
            'de': 'Statistiken zurücksetzen',
            'fr': 'Réinitialiser les Statistiques'
        },
        'gateway_enter_id': {
            'en': 'Please enter an ID',
            'pt': 'Por favor, insira um ID',
            'es': 'Por favor, ingrese un ID',
            'de': 'Bitte geben Sie eine ID ein',
            'fr': 'Veuillez entrer un ID'
        },
        'gateway_invalid_id': {
            'en': 'Invalid ID format',
            'pt': 'Formato de ID inválido',
            'es': 'Formato de ID inválido',
            'de': 'Ungültiges ID-Format',
            'fr': 'Format d\'ID invalide'
        },
        'gateway_select_rule': {
            'en': 'Please select a rule to remove',
            'pt': 'Por favor, selecione uma regra para remover',
            'es': 'Por favor, seleccione una regla para eliminar',
            'de': 'Bitte wählen Sie eine Regel zum Entfernen',
            'fr': 'Veuillez sélectionner une règle à supprimer'
        },
        'gateway_fill_all_fields': {
            'en': 'Please fill all fields',
            'pt': 'Por favor, preencha todos os campos',
            'es': 'Por favor, complete todos los campos',
            'de': 'Bitte füllen Sie alle Felder aus',
            'fr': 'Veuillez remplir tous les champs'
        },
        'gateway_invalid_values': {
            'en': 'Invalid values entered',
            'pt': 'Valores inválidos inseridos',
            'es': 'Valores inválidos ingresados',
            'de': 'Ungültige Werte eingegeben',
            'fr': 'Valeurs invalides saisies'
        },
        'menu_gateway': {
            'en': 'Gateway',
            'pt': 'Gateway',
            'es': 'Gateway',
            'de': 'Gateway',
            'fr': 'Gateway'
        },
        
        # Split-Screen Monitor
        'split_screen_mode': {
            'en': 'Split-Screen Mode',
            'pt': 'Modo Tela Dividida',
            'es': 'Modo Pantalla Dividida',
            'de': 'Geteilter Bildschirm',
            'fr': 'Mode Écran Partagé'
        },
        'split_screen_enable': {
            'en': 'Enable Split-Screen',
            'pt': 'Ativar Tela Dividida',
            'es': 'Activar Pantalla Dividida',
            'de': 'Geteilten Bildschirm aktivieren',
            'fr': 'Activer l\'Écran Partagé'
        },
        'split_screen_left': {
            'en': 'Left Panel',
            'pt': 'Painel Esquerdo',
            'es': 'Panel Izquierdo',
            'de': 'Linkes Panel',
            'fr': 'Panneau Gauche'
        },
        'split_screen_right': {
            'en': 'Right Panel',
            'pt': 'Painel Direito',
            'es': 'Panel Derecho',
            'de': 'Rechtes Panel',
            'fr': 'Panneau Droit'
        },
        'split_screen_channel': {
            'en': 'Channel: {channel}',
            'pt': 'Canal: {channel}',
            'es': 'Canal: {channel}',
            'de': 'Kanal: {channel}',
            'fr': 'Canal: {channel}'
        },
        
        # Gateway - Message Modification
        'gateway_modification': {
            'en': 'Message Modification',
            'pt': 'Modificação de Mensagens',
            'es': 'Modificación de Mensajes',
            'de': 'Nachrichtenänderung',
            'fr': 'Modification de Messages'
        },
        'gateway_add_modify': {
            'en': 'Add Modify Rule',
            'pt': 'Adicionar Regra',
            'es': 'Agregar Regla',
            'de': 'Regel hinzufügen',
            'fr': 'Ajouter Règle'
        },
        'gateway_remove': {
            'en': 'Remove',
            'pt': 'Remover',
            'es': 'Eliminar',
            'de': 'Entfernen',
            'fr': 'Supprimer'
        },
        'gateway_new_id': {
            'en': 'New ID',
            'pt': 'Novo ID',
            'es': 'Nuevo ID',
            'de': 'Neue ID',
            'fr': 'Nouvel ID'
        },
        'gateway_data_mask': {
            'en': 'Data Mask',
            'pt': 'Máscara de Dados',
            'es': 'Máscara de Datos',
            'de': 'Datenmaske',
            'fr': 'Masque de Données'
        },
        'gateway_modify_rule_title': {
            'en': 'Configure Message Modification',
            'pt': 'Configurar Modificação de Mensagem',
            'es': 'Configurar Modificación de Mensaje',
            'de': 'Nachrichtenänderung konfigurieren',
            'fr': 'Configurer Modification de Message'
        },
        'gateway_message_info': {
            'en': 'Message Information',
            'pt': 'Informações da Mensagem',
            'es': 'Información del Mensaje',
            'de': 'Nachrichteninformation',
            'fr': 'Information du Message'
        },
        'gateway_id_modification': {
            'en': 'ID Modification',
            'pt': 'Modificação de ID',
            'es': 'Modificación de ID',
            'de': 'ID-Änderung',
            'fr': 'Modification d\'ID'
        },
        'gateway_change_id': {
            'en': 'Change ID',
            'pt': 'Alterar ID',
            'es': 'Cambiar ID',
            'de': 'ID ändern',
            'fr': 'Changer ID'
        },
        'gateway_data_modification': {
            'en': 'Data Modification (Bit-Level)',
            'pt': 'Modificação de Dados (Nível de Bit)',
            'es': 'Modificación de Datos (Nivel de Bit)',
            'de': 'Datenänderung (Bit-Ebene)',
            'fr': 'Modification de Données (Niveau Bit)'
        },
        'gateway_data_modification_info': {
            'en': 'Select bytes to modify and set their values. You can edit hex values or toggle individual bits.',
            'pt': 'Selecione os bytes a modificar e defina seus valores. Você pode editar valores hex ou alternar bits individuais.',
            'es': 'Seleccione los bytes a modificar y establezca sus valores. Puede editar valores hex o alternar bits individuales.',
            'de': 'Wählen Sie die zu ändernden Bytes aus und legen Sie ihre Werte fest. Sie können Hex-Werte bearbeiten oder einzelne Bits umschalten.',
            'fr': 'Sélectionnez les octets à modifier et définissez leurs valeurs. Vous pouvez éditer les valeurs hex ou basculer les bits individuels.'
        },
        'gateway_modify_this_byte': {
            'en': 'Modify this byte',
            'pt': 'Modificar este byte',
            'es': 'Modificar este byte',
            'de': 'Dieses Byte ändern',
            'fr': 'Modifier cet octet'
        },
        'gateway_bits': {
            'en': 'Bits',
            'pt': 'Bits',
            'es': 'Bits',
            'de': 'Bits',
            'fr': 'Bits'
        },
        'gateway_preview': {
            'en': 'Preview',
            'pt': 'Visualização',
            'es': 'Vista Previa',
            'de': 'Vorschau',
            'fr': 'Aperçu'
        },
        'gateway_original': {
            'en': 'Original',
            'pt': 'Original',
            'es': 'Original',
            'de': 'Original',
            'fr': 'Original'
        },
        'gateway_modified': {
            'en': 'Modified',
            'pt': 'Modificado',
            'es': 'Modificado',
            'de': 'Geändert',
            'fr': 'Modifié'
        },
        'gateway_bytes_modified': {
            'en': 'Bytes to be modified',
            'pt': 'Bytes a serem modificados',
            'es': 'Bytes a modificar',
            'de': 'Zu ändernde Bytes',
            'fr': 'Octets à modifier'
        },
        
        # File Type Validation
        'file_type_tracer': {
            'en': 'Tracer Log',
            'pt': 'Log de Tracer',
            'es': 'Registro de Tracer',
            'de': 'Tracer-Protokoll',
            'fr': 'Journal Tracer'
        },
        'file_type_monitor': {
            'en': 'Monitor Log',
            'pt': 'Log de Monitor',
            'es': 'Registro de Monitor',
            'de': 'Monitor-Protokoll',
            'fr': 'Journal Monitor'
        },
        'file_type_transmit': {
            'en': 'Transmit List',
            'pt': 'Lista de Transmissão',
            'es': 'Lista de Transmisión',
            'de': 'Sendeliste',
            'fr': 'Liste de Transmission'
        },
        'file_type_gateway': {
            'en': 'Gateway Configuration',
            'pt': 'Configuração de Gateway',
            'es': 'Configuración de Gateway',
            'de': 'Gateway-Konfiguration',
            'fr': 'Configuration Gateway'
        },
        'msg_wrong_file_type': {
            'en': 'Wrong file type!\n\nFile: {filename}\nExpected: {expected}\nFound: {found}\n\nPlease load the correct file type.',
            'pt': 'Tipo de arquivo incorreto!\n\nArquivo: {filename}\nEsperado: {expected}\nEncontrado: {found}\n\nPor favor, carregue o tipo correto de arquivo.',
            'es': 'Tipo de archivo incorrecto!\n\nArchivo: {filename}\nEsperado: {expected}\nEncontrado: {found}\n\nPor favor, cargue el tipo correcto de archivo.',
            'de': 'Falscher Dateityp!\n\nDatei: {filename}\nErwartet: {expected}\nGefunden: {found}\n\nBitte laden Sie den richtigen Dateityp.',
            'fr': 'Type de fichier incorrect!\n\nFichier: {filename}\nAttendu: {expected}\nTrouvé: {found}\n\nVeuillez charger le bon type de fichier.'
        },
        'gateway_save_config': {
            'en': 'Save Gateway Configuration',
            'pt': 'Salvar Configuração do Gateway',
            'es': 'Guardar Configuración del Gateway',
            'de': 'Gateway-Konfiguration speichern',
            'fr': 'Enregistrer Configuration Gateway'
        },
        'gateway_load_config': {
            'en': 'Load Gateway Configuration',
            'pt': 'Carregar Configuração do Gateway',
            'es': 'Cargar Configuración del Gateway',
            'de': 'Gateway-Konfiguration laden',
            'fr': 'Charger Configuration Gateway'
        },
        'gateway_config_saved': {
            'en': 'Gateway configuration saved: {filename}',
            'pt': 'Configuração do Gateway salva: {filename}',
            'es': 'Configuración del Gateway guardada: {filename}',
            'de': 'Gateway-Konfiguration gespeichert: {filename}',
            'fr': 'Configuration Gateway enregistrée: {filename}'
        },
        'gateway_config_loaded': {
            'en': 'Gateway configuration loaded: {filename}',
            'pt': 'Configuração do Gateway carregada: {filename}',
            'es': 'Configuración del Gateway cargada: {filename}',
            'de': 'Gateway-Konfiguration geladen: {filename}',
            'fr': 'Configuration Gateway chargée: {filename}'
        },
        'success': {
            'en': 'Success',
            'pt': 'Sucesso',
            'es': 'Éxito',
            'de': 'Erfolg',
            'fr': 'Succès'
        },
        'gateway_channel_info': {
            'en': 'ℹ️ Source channel is automatically determined by transmission direction. Rules apply to messages being forwarded.',
            'pt': 'ℹ️ O canal de origem é determinado automaticamente pela direção de transmissão. Regras se aplicam às mensagens sendo encaminhadas.',
            'es': 'ℹ️ El canal de origen se determina automáticamente por la dirección de transmisión. Las reglas se aplican a los mensajes que se reenvían.',
            'de': 'ℹ️ Der Quellkanal wird automatisch durch die Übertragungsrichtung bestimmt. Regeln gelten für weitergeleitete Nachrichten.',
            'fr': 'ℹ️ Le canal source est automatiquement déterminé par la direction de transmission. Les règles s\'appliquent aux messages transmis.'
        },
        'gateway_source_channel': {
            'en': 'Source',
            'pt': 'Origem',
            'es': 'Origen',
            'de': 'Quelle',
            'fr': 'Source'
        },
        'gateway_block_id': {
            'en': 'Block ID',
            'pt': 'Bloquear ID',
            'es': 'Bloquear ID',
            'de': 'ID sperren',
            'fr': 'Bloquer ID'
        },
        'gateway_modify_id': {
            'en': 'Modify ID',
            'pt': 'Modificar ID',
            'es': 'Modificar ID',
            'de': 'ID ändern',
            'fr': 'Modifier ID'
        },
        'gateway_configure_transmission_first': {
            'en': 'Please configure transmission direction first (CAN1→CAN2 or CAN2→CAN1).',
            'pt': 'Por favor, configure a direção de transmissão primeiro (CAN1→CAN2 ou CAN2→CAN1).',
            'es': 'Por favor, configure la dirección de transmisión primero (CAN1→CAN2 o CAN2→CAN1).',
            'de': 'Bitte konfigurieren Sie zuerst die Übertragungsrichtung (CAN1→CAN2 oder CAN2→CAN1).',
            'fr': 'Veuillez d\'abord configurer la direction de transmission (CAN1→CAN2 ou CAN2→CAN1).'
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
