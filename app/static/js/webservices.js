// Define the default location of webservices

function getDefaultServicesPrefix() {
	
    // если отлаживаем локально, то сервисы ищем на 8080 порту
	/***
	var servername = 'https://'+document.domain;
	if (String(document.domain).indexOf('127.0.0.1')!=-1 || String(document.domain).indexOf('192.168.')!=-1 )
		servername += ':8080';
	***/
	var servername = "https://cimm.kpfu.ru";
	var webapp = "/webservices";
	return servername + webapp;
}

function getDefaultServices() {
	var base = getDefaultServicesPrefix();
	var services = {
			"clean2dws" : base + "/rest-v0/util/convert/clean",
			"clean3dws" : base + "/rest-v0/util/convert/clean",
			"molconvertws" : base + "/rest-v0/util/calculate/molExport",
			"stereoinfows" : base + "/rest-v0/util/calculate/cipStereoInfo",
			"reactionconvertws" : base + "/rest-v0/util/calculate/reactionExport",
			"hydrogenizews" : base + "/rest-v0/util/convert/hydrogenizer",
			"automapperws" : base + "/rest-v0/util/convert/reactionConverter"
	};
	return services;
}

