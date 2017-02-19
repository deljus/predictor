// Define the default location of webservices

function getDefaultServicesPrefix() {
    return "https://cimm.kpfu.ru/webservices";
}

function getApiUrl() {
    return '/api';
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
