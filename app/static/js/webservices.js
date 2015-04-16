// Define the default location of webservices

function getDefaultServicesPrefix() {
	
	// ��� ������� ������� ����� �� 8080 �����, � ���������� - �� 80
	if (String(document.domain).indexOf('127.0.0.1')!=-1)
		var servername = 'http://127.0.0.1:8080';
	else
		var servername = '';
		
	var webapp = "/webservices";
	return servername + webapp;
}

function getDefaultServices() {
	var base = getDefaultServicesPrefix();
	console.log(base);
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

