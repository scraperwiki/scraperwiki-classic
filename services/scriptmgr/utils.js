/******************************************************************************
* utils.js
*
* Utility functions for working with the processes locally
******************************************************************************/
var exts = {
	'python' : 'py', 
	'ruby'   : 'rb', 	
	'php'   : 'php', 		
}

exports.extension_for_language = function( lang ) {
	return exts[lang];
};

exports.env_for_language = function( lang, extra_path ) {
	if ( lang == 'python' ) {
		return {PYTHONPATH: extra_path, PYTHONUNBUFFERED: 'true'};
	}
};

				