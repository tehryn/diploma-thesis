/* jshint esversion: 8 */
/* jshint node: true */
/* jshint browser: true */
/* jshint -W080 */

var browser = browser || chrome;
/*
On startup, connect to the "ping_pong" app.
*/
let port = browser.runtime.connectNative("GnuPG_Decryptor");

/*
Listen for messages from the app.
*/
port.onMessage.addListener(
    ( message ) => {
        console.log( message );
        if ( message.type === 'decryptResponse' ){
            browser.tabs.query({active: true, currentWindow: true}, function(tabs) {
                // console.log( tabs );
                browser.tabs.sendMessage( tabs[0].id, message, null );
            });
        }
        //browser.runtime.sendMessage( 'GnuPG_Decryptor@stud.fit.vutbr.cz', { 'data' : message.data, 'encoding' : message.encoding, type : 'decryptResponse', success : message.success }, null );
    }
);

browser.runtime.onMessage.addListener(
    function( message, sender, sendResponse ) {
        // console.log( message );
        // console.log( sender );
        if ( message.type === "decryptRequest" ) {
            port.postMessage( { 'data' : message.data, 'encoding' : message.encoding, 'messageId' : message.messageId, 'type' : 'decryptRequest' } );
        }
    }
);