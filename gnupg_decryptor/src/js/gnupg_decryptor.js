/* jshint esversion: 8 */
/* jshint node: true */
/* jshint browser: true */
/* jshint -W080 */

const encoder = new TextEncoder();

var browser = browser || chrome;
let elemId  = 0;
let elements  = {};

document.body.style.border = "5px solid blue";
browser.runtime.onMessage.addListener(
    function( message, sender, sendResponse ) {
        console.log( message );
        if ( message.type === "decryptResponse" ) {
            if ( message.success === 1 ) {
                let blob  = new Blob( [base64ToArrayBuffer( message.data )], { type : "image/jpg" } );
                let url = URL.createObjectURL( blob );
                let elem = document.getElementById( message.messageId );
                console.log( url );
                console.log( elem );
                elem.src = url;
            }
        }
    }
);


main();

function getId() {
    return 'GnuPG_DecryptorElemId-' + elemId++;
}

function main() {
    let elements = getElements();
    elements.forEach(
        function( elem, index ) {
            let id = elem.data.id;
            if ( !elem.id ) {
                elem.data.id = id = getId();
            }
            console.log( id );
            if ( elem.type === 'img' ) {
                img = elem.data;
                console.log( img );
                // We are working with encrypted images
                let reader = new FileReader();
                
                // reading the file
                reader.onload = function(event) {
                    let encrypted = arrayBufferToBase64( event.target.result );
                    let message   = { 'data' : encrypted, 'type' : 'decryptRequest', encoding : 'base64', messageId : id };
                    browser.runtime.sendMessage( message );
                };
                
                // getting the file as blob
                getFile( img.src, 'blob' ).then(
                    function( data ) {
                        reader.readAsArrayBuffer( data );
                    }
                );
            }
        }
    );
}

function mergeArrayBuffers( arr1, arr2, arr3 ) {
    let result = new Uint8Array( arr1.byteLength + arr2.byteLength + arr3.byteLength );
    result.set( new Uint8Array( arr1 ), 0 );
    result.set( new Uint8Array( arr2 ), arr1.byteLength );
    result.set( new Uint8Array( arr3 ), arr1.byteLength + arr2.byteLength );
    return result.buffer;
}

function getElements() {
    let arr = [];
    
    // images
    let images = document.getElementsByTagName( 'img' );
    
    for ( let i = 0; i < images.length; i++ ) {
        if ( images[i].src.toLowerCase().endsWith( '.gpg' ) ) {
            arr.push( { 'data' : images[i], 'type' : 'img' } );
        }
    }

    // div and span backgrounds
    // TODO
    
    return arr;
}

function getFile( url, type ) {
    return new Promise(
        function(resolve, reject) {
            try {
                let xhr = new XMLHttpRequest();
                xhr.open( 'GET', url );
                xhr.responseType = type;
                xhr.onerror = function() {
                    reject( 'Network error.' );
                };
                xhr.onload = function() {
                    if ( xhr.status === 200 ) {
                        resolve(xhr.response);
                    }
                    else {
                        reject( 'Loading error:' + xhr.statusText );
                    }
                };
                xhr.send();
            }
            catch( err ) {
                reject( err.message );
            }
        }
    );
}

function arrayBufferToBase64( buffer ) {
    var binary = '';
    var bytes = new Uint8Array( buffer );
    var len = bytes.byteLength;
    for (var i = 0; i < len; i++) {
        binary += String.fromCharCode( bytes[ i ] );
    }
    return window.btoa( binary );
}

function base64ToArrayBuffer(base64) {
    var binary_string = window.atob(base64);
    var len = binary_string.length;
    var bytes = new Uint8Array(len);
    for (var i = 0; i < len; i++) {
        bytes[i] = binary_string.charCodeAt(i);
    }
    return bytes.buffer;
}

function readAllChunks(readableStream) {
  const reader = readableStream.getReader();
  const chunks = [];

  function pump() {
    return reader.read().then(({ value, done }) => {
      if (done) {
        return chunks;
      }
      chunks.push(value);
      return pump();
    });
  }

  return pump();
}