import sys
from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget, QLabel, QTableWidget, QTableWidgetItem, QBoxLayout, QLineEdit, QMainWindow, QCheckBox, QPushButton
from PyQt5.QtGui import QIcon, QFont

class GnuPG_Decryptor_GUI( QWidget ):
    def __init__( self, app, initKeys = [] ):
        super().__init__()
        self._backend = app
        self._sudo    = None
        self._homedir = None
        self.initUI( initKeys )

    def resizeEvent( self, event ):
        self._keyList.setMaximumSize( self.width(), self.height() * 0.66 )

    def initUI( self, initKeys ):
        self.setWindowIcon( QIcon( './icon/gnupg_256.png' ) )
        self.setWindowTitle( 'GnuPG_Decryptor' )
        self.setMinimumSize( 700, 350 )
        self.center()
        self._keyList   = KeyList( self, initKeys )
        self._refresher = Refresher( self )

        self._layout = QBoxLayout( QBoxLayout.TopToBottom, parent = self )
        self._layout.addWidget( self._keyList )
        self._layout.addWidget( self._refresher )

        self.setLayout( self._layout )
        self.show()

    def center( self ):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter( cp )
        self.move( qr.topLeft() )

    def notifyBackend( self, message ):
        if ( message[ 'action' ] == 'refresh' ):
            data = self._backend.keyList( message )
            if ( data[ 'returnCode' ] == 0 ):
                sudo = message['sudo']['password']    if message[ 'sudo' ][ 'use' ] else None
                home = message['home']['homedir'] if message[ 'home' ][ 'use' ] else None
                self._keyList.newKeys( data[ 'keys' ], sudo, home )
        elif ( message[ 'action' ] == 'confirm' ):
            self._backend.setPasswords( message )
            self.close()

class KeyList( QWidget ):
    def __init__( self, parent, initKeys ):
        super().__init__( parent )
        self._parent  = parent
        self._keys    = []
        self._sudo    = None
        self._homedir = None
        self.initUI()
        self.newKeys( initKeys )

    def initUI( self ):
        font = QFont()
        font.setBold( True )
        self._label = QLabel( 'Available Keys', self )
        self._label.setFont( font )
        self._label.setMaximumHeight( KeyItem.itemHeight() )
        self._layout = QBoxLayout( QBoxLayout.TopToBottom, parent = self )
        self._layout.setSpacing(5)
        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout( self._layout )
        self._layout.addWidget( self._label )

        self._button = QPushButton( "Confirm" )
        self._button.setMaximumWidth( 80 )
        self._button.clicked.connect( self.confirm )
        self._noKeys = QLabel( 'No keys found.' )

        self._layout.addWidget( self._noKeys )
        self._layout.addWidget( self._button )
        self._layout.addStretch( 1 )


    def confirm( self ):
        keys = list()
        for key in self._keys:
            keys.append( { 'id' : key.getId(), 'password' : key.getPass() } )

        useSudo = 0 if self._sudo    is None else 1
        useHome = 0 if self._homedir is None else 1
        sudo    = self._sudo    if useSudo else ''
        homedir = self._homedir if useHome else ''
        message = { 'action' : 'confirm', 'keys' : keys, 'sudo' : { 'use' : useSudo, 'password' : sudo }, 'home' : { 'use' : useHome, 'homedir' : homedir } }
        self._parent.notifyBackend( message )

    def newKeys( self, keys, sudo = None, homedir = None ):
        self._sudo    = sudo
        self._homedir = homedir
        self.clearList()
        if ( len( keys ) > 0 ):
            self._noKeys.hide()
            for key in keys:
                self.newKey( key )
        else:
            self._noKeys.show()

    def clearList( self ):
        for item in self._keys:
            self._layout.removeWidget( item )
            item.deleteLater()
        self._keys = []

    def newKey( self, key ):
        item = KeyItem( key, self )
        self._layout.insertWidget( self._layout.count() - 2, item )
        self._keys.append( item )

class KeyItem( QWidget ):
    @staticmethod
    def itemHeight():
        return 20

    @staticmethod
    def itemWidths():
        return [ 350, 300 ]

    def __init__( self, key, parent ):
        super().__init__( parent )
        self._parent = parent
        self._id = key[ 'id' ]
        self.initUI( key[ 'password' ] )

    def initUI( self, password ):
        self.setMinimumHeight( KeyItem.itemHeight() )
        self.setMaximumHeight( KeyItem.itemHeight() )
        self._labelId        = QLabel( self._id, self )
        self._labelPassText  = QLabel( 'Password: ', self )
        self._labelPass      = QLineEdit( self )
        self._layout         = QBoxLayout( QBoxLayout.LeftToRight, parent = self )
        self._labelPass.setEchoMode( QLineEdit.Password )
        self._labelPass.setText( password )
        widths = KeyItem.itemWidths()
        self._labelId.setMaximumWidth( widths[0] )
        self._labelId.setMinimumWidth( widths[0] )
        #self._labelPass.setMaximumWidth( widths[2] )
        #self._labelPass.setMinimumWidth( widths[2] )
        self._layout.addWidget( self._labelId  )
        self._layout.addWidget( self._labelPassText  )
        self._layout.addWidget( self._labelPass  )
        self._layout.addStretch( 1  )
        self._layout.setContentsMargins( 10, 0, 0, 0 )
        self.setLayout( self._layout )

    def getPass( self ):
        return self._labelPass.text()

    def getId( self ):
        return self._id

    def setIdWidth( self, width ):
        self._labelId.setMaximumWidth( width )

class Refresher( QWidget ):
    def __init__( self, parent ):
        super().__init__( parent )
        self.initUI()
        self._parent = parent

    def initUI( self ):
        font = QFont()
        font.setBold( True )
        self._label = QLabel( 'Refresh Keys', self )
        self._label.setFont( font )

        self._sudoWidget = QWidget( self )
        self._sudoWidget.hide()
        sudoLayout = QBoxLayout( QBoxLayout.LeftToRight, parent = self._sudoWidget )
        self._sudoWidget.setLayout( sudoLayout )

        self._homeWidget = QWidget( self )
        self._homeWidget.hide()
        homeLayout = QBoxLayout( QBoxLayout.LeftToRight, parent = self._homeWidget )
        self._homeWidget.setLayout( homeLayout )

        self._sudo = QLineEdit( self._sudoWidget )
        self._sudo.setMaximumWidth( 300 )
        self._sudo.setEchoMode( QLineEdit.Password )

        sudoLabel = QLabel( "sudo:  ", parent = self._sudoWidget )
        sudoLayout.addWidget( sudoLabel )
        sudoLayout.addWidget( self._sudo )
        sudoLayout.addStretch( 1 )
        sudoLayout.setContentsMargins( 0, 0, 0, 0)

        self._home = QLineEdit( self._homeWidget )
        self._home.setMaximumWidth( 300 )

        homeLabel = QLabel( "home:", parent = self._homeWidget )
        homeLayout.addWidget( homeLabel )
        homeLayout.addWidget( self._home )
        homeLayout.addStretch( 1 )
        homeLayout.setContentsMargins( 0, 0, 0, 0)


        self._sudoChck  = QCheckBox( 'Use sudo to access private keys', parent = self )
        self._homeChck  = QCheckBox( 'Use homedir parameter for gpg', parent = self )
        self._sudoChck.toggled.connect( self.toggleChck )
        self._homeChck.toggled.connect( self.toggleChck )

        self._button = QPushButton( "Refresh" )
        self._button.setMaximumWidth( 80 )
        self._button.clicked.connect( self.refresh )

        self._layout = QBoxLayout( QBoxLayout.TopToBottom, parent = self )
        self._layout.setSpacing(5)
        self._layout.setContentsMargins( 0, 0, 0, 0 )
        self.setLayout( self._layout )
        self._layout.addWidget( self._label )
        self._layout.addWidget( self._sudoChck )
        self._layout.addWidget( self._homeChck )
        self._layout.addWidget( self._sudoWidget )
        self._layout.addWidget( self._homeWidget )
        self._layout.addWidget( self._button )
        self._layout.addStretch( 1 )

    def refresh( self ):
        useSudo = self._sudoChck.isChecked()
        sudo    = self._sudo.text() if useSudo else None
        useHome = self._homeChck.isChecked()
        home    = self._home.text() if useHome else None
        message = {
            'action' : 'refresh',
            'sudo' : { 'use' : useSudo, 'password' : sudo },
            'home' : { 'use' : useHome, 'homedir'  : home }
        }
        self._parent.notifyBackend( message )

    def toggleChck( self ):
        if ( self._sudoChck.isChecked() ):
            self._sudoWidget.show()
        else:
            self._sudoWidget.hide()

        if ( self._homeChck.isChecked() ):
            self._homeWidget.show()
        else:
            self._homeWidget.hide()