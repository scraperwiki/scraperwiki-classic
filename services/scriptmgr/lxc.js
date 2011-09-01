/******************************************************************************
* lxc.js
*
* Abstracts running the provided code through an lxc instance. We make sure at
* initialisation that all of the LXCs that we expect are created and running.
* 
******************************************************************************/
var _    = require('underscore')._;
var mu   = require('mu');
var fs   = require('fs');
var spawn = require('child_process').spawn;
var util  = require('./utils.js');
var path  = require('path');

// All of our virtual machines
var vms = [ ]; // vm name -> objects


var vms_by_ip    = [ ]; // maps of ip -> vm name
var vms_by_runid = [ ]; // maps of runid -> vm name

var root_folder = '';

var config_tpl = '';
var fstab_tpl  = '';


/******************************************************************************
* Initialise the LXC handling by storing some properties and caching some 
* templates ( only until we have created the relevant config files ).
******************************************************************************/
exports.init = function(count, lxc_root_folder) {
	root_folder = lxc_root_folder;
	
	config_tpl = fs.readFileSync( './templates/config.tpl', "utf-8");
	fstab_tpl = fs.readFileSync('./templates/fstab.tpl', "utf-8");

	vms = _.map( _.range(1, count + 1), function(num){ return 'vm' + num; } );	
	_.map( vms, function(v) { create_vm(v); } );
};


/******************************************************************************
* Execute the provided code on an lxc instance if we can get one.
******************************************************************************/
exports.exec = function(script, code) {
	// execute lxc-execute on a vm, after we've been allocated on
	var name = allocate_vm( script );
	// clean up the files that may still be there.....
	var cf = get_code_folder(name);
	// delete the contents of cf

	// TODO: Fix this and only unlink if exists
	try {
		fs.unlinkSync( path.join(cf, 'script.py') );
	} catch(e){}

	try {
		fs.unlinkSync( path.join(cf, 'script.rb') );
	} catch(e){}		
	try {	
		fs.unlinkSync( path.join(cf, 'script.php') );
	} catch(e){}			
	try {	
		fs.unlinkSync( path.join(cf, 'script.js') );			
	} catch(e){}			
	
	return name;
};


/******************************************************************************
* Kill the LXC instance that is currently running the provided script
******************************************************************************/
exports.kill = function( script ) {
		console.log('looking for ' + script.run_id );
	var vm = vms_by_runid[ script.run_id ];
	if ( vm ) {
		// trigger an lxc-kill
		// lxc-stop -n 'vm'
		e = spawn('/usr/bin/lxc-stop', ['-n', vm]);

		// Clean up indices
		delete vms_by_run_id[ script.run_id ];		
		delete vms_by_ip[ script.ip ];
	}
	return false;
};


exports.code_folder = get_code_folder = function(name) {
	return path.join(root_folder, name + '/code/');
}

exports.ip_for_vm = function(name) {
	var num = parseInt( name.substring(2) );
	return '10.0.1.' + (num + 1).toString();
}

/*****************************************************************************
* Create a new VM based on newly created config files - if not already created
******************************************************************************/
function create_vm ( name ) {

	var v = {
		'name': name,
		'running': false,
		'script': null,		
	}
	
	// if name exists then just return, otherwise integrate templates and then
	// lxc-create.  Bear in mind that currently (and naffly) the IP address 
	// will be the vm number + 1 (as vm0 has ip 10.0.1.1 )

	// write config and fstab to ...	
	var folder = path.join(root_folder, name);
	
	num = parseInt( name.substring(2) );
	
	// TODO: Fix me
	var ctx = {'name': name, 'ip': '10.0.1.' + (num + 1).toString() }


	var compiled = _.template( config_tpl );
	var cfg = compiled( ctx );
	
	var fs_compiled = _.template( fstab_tpl );
	var fstab = fs_compiled( ctx );
	
	path.exists(root_folder, function (exists) {	
  		if ( ! exists ) {
			fs.mkdirSync( root_folder, "0777" );
		}	
	});
	
	
	path.exists(folder, function (exists) {
  		if ( ! exists ) {
			fs.mkdirSync( folder, "0777" );
		} else {
			return;
		}

		// Mount a specific code folder
		var cfolder = get_code_folder(name);
		path.exists(cfolder, function (exists) {
	  		if ( ! exists ) fs.mkdirSync( cfolder, "0777" );
		});

		var tgt = path.join( folder, 'config')
		fs.writeFile(tgt, cfg, function(err) {
		    if(err) {
		        sys.puts(err);
		    } else {
				console.log('Running lxc-create')
				// call lxc-create -n name -f folder/config
			 	e = spawn('/usr/bin/lxc-create', ['-n', name, '-f', tgt]);
				e.on('exit', function (code, signal) {
					if ( code && code == 127 ) {
						util.log.fatal('LXC-Create exited with code ' + code);											
					} else {
						util.log.info('LXC-Create exited with code ' + code);																	
					}
				});
		    }
		});
					
		tgt = path.join( folder, 'fstab')
		console.log('Writing fstab to ' + tgt);	
		fs.writeFile(tgt, fstab, function(err) {
		    if(err) {
		        sys.puts(err);
		    } else {
		    }
		});	
	});
	
	return v;
}



/*****************************************************************************
* Release the VM using the provided script. 
*****************************************************************************/
function release_vm ( script, name ) {
	var k;
	
	for ( var key in vms ) {
		var vm = vms[key];
		k = key;
		if ( ! vm.script.run_id == script.run_id ) {
			v = vm;
			break;
		};
	}

	if ( ! v ) {
		return;
	};

	// Remove it from the two lookup tables
	delete vms_by_runid[ script.run_id ]
	delete vms_by_ip[ script.ip ]
	
	v.running = false;
	v.script = null;
	vms[k] = v;
}

/*****************************************************************************
* Allocate a vm to the calling script.  We will check to find one that isn't
* running and either allocate it or return null if none are found.
*
* TODO: Fix this and use detect
* i.e.
* var even = _.detect([1, 2, 3, 4, 5, 6], function(num){ return num % 2 == 0; });
* => 2
******************************************************************************/
var current = 1;
function allocate_vm ( script ) {
	
	var max = vms.length;
	if ( current >= max ) {
		current = 1;
	}
	
	return vms[current++];
	
/*	var v, k;
	for ( var key in vms ) {
		var vm = vms[key];
		k = key;
		if ( vm.running == false ) {
			v = vm;
			break;
		};
	}
	
	if ( ! v ) {
		return null;
	};
	
	v.running = true;
	v.script = script;
	vms[k] = v;
	return v*/
}
