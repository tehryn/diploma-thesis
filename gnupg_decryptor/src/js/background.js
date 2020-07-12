/* jshint esversion: 8 */
/* jshint node: true */
/* jshint browser: true */
/* jshint -W080 */

var browser     = browser || chrome;
var keys        = {};
var sizeCounter = 0;

const MAXIMUM_SIZE = 4 * 1024 * 1024 * 1024;

let port = browser.runtime.connectNative( "GnuPG_Decryptor" );
//console.log( port );
/*
Listen for messages from the app.
*/
receiverId = null;
port.onMessage.addListener(
    ( message ) => {
        if ( message.type === 'decryptResponse' ){
            console.log( message );
            browser.tabs.sendMessage( message.tabId, message, null );
        }
        else if ( message.type === 'debug' ) {
            console.log( message );
        }
        else if ( message.type === 'updateKeysRequest' ) {
            keys = message.keys;
        }
        else if ( message.type === 'getKeysRequest' ) {
            response = { 'type' : 'getKeysResponse', 'keys' : keys };
            port.postMessage( response );
        }
        //browser.runtime.sendMessage( 'GnuPG_Decryptor@stud.fit.vutbr.cz', { 'data' : message.data, 'encoding' : message.encoding, type : 'decryptResponse', success : message.success }, null );
    }
);

browser.runtime.onMessage.addListener(
    function( message, sender, sendResponse ) {
        console.log( message );
        //console.log( sender );
        if ( message.type === "decryptRequest" ) {
            port.postMessage( message );
        }
        else if ( message.type === "tabIdRequest" ) {
            browser.tabs.sendMessage( sender.tab.id, { 'type' : 'tabIdResponse', 'tabId' : sender.tab.id }, null );
        }
    }
);

browser.browserAction.onClicked.addListener(
    function() {
        port.postMessage( { 'type' : 'displayWindow' } );
    }
);