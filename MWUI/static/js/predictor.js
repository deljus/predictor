/******************************************************/

//class TaskType(Enum):
TaskType = {
    MODELING: 0
    , SIMILARITY: 1
    , SUBSTRUCTURE: 2
}


//class ModelType(Enum):
ModelType = {
    PREPARER: 0
    , MOLECULE_MODELING: 1
    , REACTION_MODELING: 2
    , MOLECULE_SIMILARITY: 3
    , REACTION_SIMILARITY: 4
    , MOLECULE_SUBSTRUCTURE: 5
    , REACTION_SUBSTRUCTURE: 6
}


//class TaskStatus(Enum):
TaskStatus = {
    NEW: 0
    , PREPARING: 1
    , PREPARED: 2
    , MODELING: 3
    , DONE: 4
}


//class StructureStatus(Enum):
StructureStatus = {
    RAW : 0,
    HAS_ERROR : 1,
    CLEAR : 2
}


var TIMER_INTERVAL = 5000;
var MOL_FORMAT = 'mrv';

var TAMER_ID;

var marvinSketcherInstance;
var isSaveMrvBtnExists = false;

var isSketcherDataChanged = false;

// все модели
var MODELS = new Array();
var API_BASE = getApiUrl();

/*
 api.add_resource(UploadTask, '/task/upload/<int:_type>')
 api.add_resource(PrepareTask, '/task/prepare/<string:task>')
 api.add_resource(ModelTask, '/task/model/<string:task>')
 # api.add_resource(ResultsTask, '/task/results/<string:task>')
 api.add_resource(AvailableAdditives, '/resources/additives')
 api.add_resource(AvailableModels, '/resources/models')
 api.add_resource(RegisterModels, '/admin/models')
 */
var ApiUrl = {
    create_model_task: API_BASE + "/task/create/" + TaskType.MODELING
    , prepare_task: API_BASE + "/task/prepare/"
    , model_task: API_BASE + "/task/model/"
    , task_result: API_BASE + "/task/results/"
    , get_models: API_BASE + "/resources/models"
    , get_additives: API_BASE + "/resources/additives"
}
/******************************************************/

function get_status_name(arr, id) {
    for (var key in arr) {
        if (arr[key]==id)
            return key;

    }
    return null;
}
function array_distinct(arr, fld) {
    var i = 0,
        l = arr.length,
        v, t, o = {}, n = [];

    for (; i < l; i++) {
        if (fld == undefined)
            v = arr[i];
        else
            v = arr[i][fld];
        t = typeof v;
        if (typeof o[v + t] == 'undefined') {

            o[v + t] = 1;
            n.push(v);
        }
    }
    return n;
};
function array_select(arr, fld, cond) {
    var ret = new Array();
    for (var i = 0; i < arr.length; i++) {
        try {
            if (arr[i][fld] == cond)
                ret.push(arr[i]);
        }
        catch (err) {
        }

    }
    return ret;
}

function reset_timer() {
    clearInterval(TAMER_ID);
}

function log_log(str) {
    try {
        if (str instanceof Error)
            console.log(str.name + ":" + str.message);
        else
            console.log(str);
    }
    catch (err) {
    }
}


function find(arr, what, where) {
    var elem = undefined;
    try {
        for (var i = 0; i < arr.length; i++) {
            elem = arr[i];
            if (where)
                elem = elem[where];
            if (elem == what)
                return i;
        }
    }
    catch (err) {
        log_log('find->' + err);
    }
    return -1;
}

/*** debug fuctions ***/
function set_task(task_id) {
    $('#task_id').val(task_id);
    setCookie('task_id', task_id);

}
function set_structure(structure_id)
{
       $('#structure_id').val(structure_id);
        setCookie('structure_id', structure_id);
}
function set_structure_data(data) {
    var structure_id = get_structure();
    $("#structure_data"+structure_id).val(encodeURIComponent(data)).attr("data-is-changed","1");
}
function get_structure_data(structure_id) {
    if (structure_id==undefined)
        structure_id = get_structure();
    return $("#structure_data"+structure_id).val();
}
function get_task() {
    var task_id = $('#task_id').val();
    if (task_id == "")
        task_id = getCookie("task_id");
    return task_id;
}
function get_structure() {
    var structure_id = $('#structure_id').val();
    if (structure_id == "")
        structure_id = getCookie("structure_id");
    return structure_id;
}
function load_reactions() {
    hide_all();
    get_prepare_task(get_task());
}

function load_results() {
    hide_all();
    get_modeling_result(get_task());
}

function map_done() {
    set_task_status(get_task(), MAPPING_DONE)
}

function model_done() {
    set_task_status(get_task(), MODELLING_DONE)
}


var Progress = {}
Progress.increase_progress = function (value) {

    //log_log('increase_progress->');
    try {
        var jPrg = $('.progress div[role=progressbar]');
        if (value)
            var prc = value;
        else {
            var prc = parseInt(jPrg.attr('aria-valuenow'));
            if (prc >= 90)
                prc = 0;

            prc += 10;
        }


        jPrg.attr('aria-valuenow', prc);
        jPrg.width(prc + '%');//.text(prc+'%');
    }
    catch (err) {
        log_log(err);
    }
}

Progress.start = function () {
    $('.progress').show();
    this.timer_id = setInterval(this.increase_progress, 1000);
}

Progress.done = function () {
    reset_timer();
    clearInterval(this.timer_id);
    this.increase_progress(100);
    setTimeout(function () {
        $('.progress').hide()
    }, 1000);
}

function handleRequestError() {
    Progress.done();
}

function download_results(format) {
    var task_id = $('#task_id').val();
    window.open(API_BASE + '/download/' + task_id + '?format=' + format);
}

function select_mode(mode) {
    hide_all();
    switch (mode) {
        case 'file':
            hide_editor();
            show_file_upload();

            break;
        case 'editor':
            hide_file_upload();
            show_editor(true);
            break;

    }
}

function upload_file(data) {
    return $.ajax({
        type: 'POST',
        url: API_BASE + '/upload',
        data: data,
        contentType: false,
        cache: false,
        processData: false,
        async: false,
    });

}

function upload_task_file_data() {
    //log_log('upload_task_file_data->');
    Progress.start();

    var form_data = new FormData($('#upload-file-form')[0]);
    upload_file(form_data).done(function (data, textStatus, jqXHR) {

        hide_file_upload();

        $("#task_id").val(data);
        start_prepare_model_task(data);

    }).fail(handleRequestError);
}

/***** ON PAGE LOAD ******/
$(function () {
    $('#upload-file-btn').click(function () {

        if ($('#file').val() == '') {
            alert('You have to select file');
            return false;
        }
        upload_task_file_data();
    });

    $("#prepare-reactions-tbd,#model-reactions-tbd").on('click', '.structure-img', function () {
        //og_log('click reaction lick');
        var $img = $(this);
        var _id = $img.attr("data-structure-id");
        var data = decodeURIComponent($("#structure_data"+_id).val());

        set_structure(this.getAttribute('data-structure-id'));
        draw_moldata(data);
    });

    // for additive control
    $('.dropdown-menu input').click(function (e) {
        e.stopPropagation();
    });
    $("#model-reactions-tbd").on("hidden.bs.dropdown", ".dropdown", function(event){
        var cur_obj = this;
        var add_arr = [];
        $(this).find('.dropdown-menu li').each(function (i,e) {

            var amount = $(e).find('input:text').val();
            if (parseFloat(amount)>0)
            {
                add_arr.push( e.getAttribute('data-additive-name') );
            }

        });
        if (add_arr.length==1)
            $(cur_obj).children('a').text(add_arr[0]);
        else if (add_arr.length>1)
        {
            $(cur_obj).children('a').text('selected ('+add_arr.length+')');
        }
        else
            $(cur_obj).children('a').text('None Selected ');

    });

});

function isEmpty(val) {
    if (val == '' || val == undefined || val == 'undefined' || val == null || val == 'null')
        return true;
    else
        return false;
}


function reactionToMrv(mol) {
    var services = getDefaultServices();
    var data = JSON.stringify({"structure": mol});
    return $.ajax({
        type: 'POST',
        url: services['automapperws'],
        contentType: 'application/json',
        data: data
    });
}

function isMolEmpty(data) {
    if (String(data).indexOf('MChemicalStruct') >= 0 || String(data).indexOf('$RXN') >= 0)
        return false;
    else
        return true;
}

function set_task_status(task_id, status) {
    //log_log('set_task_status->'+status);
    var data = JSON.stringify({"task_status": status});
    return $.ajax({
        "url": API_BASE + "/task_status/" + task_id
        , "type": "PUT"
        , "dataType": "json"
        , "contentType": "application/json"
        , "data": data
    });
}

function get_task_status(task_id) {
    //log_log('get_task_status->'+task_id);
    return $.get(API_BASE + "/task_status/" + task_id);
}

function get_prepare_task_status(task_id) {
    //log_log('get_task_status->'+task_id);
    return $.get(API_BASE + "/task/prepare/" + task_id);
}



function get_solvents() {
    return $.get(API_BASE + "/solvents");
}

function get_reactions_by_task(task_id) {
    return $.get(API_BASE + "/task_reactions/" + task_id)
}

function get_model(model_id) {
    return $.get(API_BASE + "/model/" + model_id)
}

function initControl() {
    // get mol button
    $("#btn-upload-sketcher-data").on("click", function (e) {
        upload_sketcher_data();
    });

    $("#btn-search-upload-sketcher-data").on("click", function (e) {
        upload_sketcher_search_data();
    });
}

function hide_all() {
    hide_select_mode();
    hide_editor();
    hide_reactions();
    hide_file_upload();
    hide_modelling_results();

}

function hide_modelling_results() {
    $('#results-div').hide();
}

function hide_select_mode() {
    $('#select-mode-div').hide(1000);
}
function hide_upload_sketcher_data_btn() {
    $('#btn-upload-sketcher-data-div').hide();
}

function show_upload_sketcher_data_btn() {
    $('#btn-upload-sketcher-data-div').show();
}

function hide_save_sketcher_data_btn() {
    $('#btn-save-sketcher-data-div').hide();
}

function show_save_sketcher_data_btn() {
    $('#btn-save-sketcher-data-div').show();
}

function hide_editor() {
    //$('#editor-div').hide();
    $('#sketch').removeClass('sketcher-frame').addClass('hidden-sketcher-frame');
    hide_upload_sketcher_data_btn();
    hide_save_sketcher_data_btn();
}

function show_editor(show_upload_reaction_button) {
    //$('#editor-div').show(1000);
    $('#sketch').removeClass('hidden-sketcher-frame').addClass('sketcher-frame');
    if (show_upload_reaction_button) {
        show_upload_sketcher_data_btn();
    }

}

function hide_reactions() {
    $('#reactions-div').hide();
}

function hide_file_upload() {
    $('#file-upload-div').hide();
}

function show_file_upload() {
    $('#file-upload-div').show(1000);
}


function upload_sketcher_data() {
    Progress.start();
    marvinSketcherInstance.exportStructure(MOL_FORMAT).then(function (source) {


        if (isMolEmpty(source)) {
            alert('You need enter a reaction');
            Progress.done();
            return false;
        }
        else
            create_model_task(source);

    }, function (error) {
        alert("Molecule export failed:" + error);
    });
}

function upload_sketcher_search_data() {
    Progress.start();
    marvinSketcherInstance.exportStructure(MOL_FORMAT).then(function (source) {


        if (isMolEmpty(source)) {
            alert('You need enter a reaction');
            Progress.done();
            return false;
        }
        else
            upload_search_task_draw_data(source);

    }, function (error) {
        alert("Molecule export failed:" + error);
    });
}


function create_model_task(draw_data) {
    //log_log('create_model_task->');
    hide_upload_sketcher_data_btn();
    hide_save_sketcher_data_btn();

    //var data = {"structures":[{"data":draw_data}]};
    var data = {"data": draw_data};
    data = JSON.stringify(data);

    $.ajax({
        "url": ApiUrl.create_model_task
        , "type": "POST"
        , "dataType": "json"
        , "contentType": "application/json"
        , "data": data
    }).done(function (resp, textStatus, jqXHR) {

        log_log('задача создана:');
        log_log(resp);
        var task_id = resp.task;
        set_task(task_id);
        start_prepare_model_task(task_id);

    }).fail(handleRequestError);
}

function upload_search_task_draw_data(draw_data) {
    //log_log('upload_search_task_draw_data->');
    hide_upload_sketcher_data_btn();
    $('#btn-upload-sketcher-data-div').hide();

    var data = JSON.stringify({"reaction_structure": draw_data, "task_type": "search"});

    $.ajax({
        "url": API_BASE + "/tasks"
        , "type": "POST"
        , "dataType": "json"
        , "contentType": "application/json"
        , "data": data
    }).done(function (data, textStatus, jqXHR) {

        //log_log('TASK_ID = '+data);
        $("#task_id").val(data);
        start_task_searching(data);

    }).fail(handleRequestError);
}

function start_prepare_model_task(task_id) {
    //log_log('start_prepare_model_task->');
    TAMER_ID = setInterval(function () {
        get_prepare_task(task_id)
    }, TIMER_INTERVAL);

}

function start_task_searching(task_id) {

    TAMER_ID = setInterval(function () {
        check_searching_task_status(task_id)
    }, TIMER_INTERVAL);

}


function check_searching_task_status(task_id) {
    //log_log('check_searching_task_status->');

    get_task_status(task_id).done(function (data, textStatus, jqXHR) {

        if (data == MODELLING_DONE) {
            reset_timer();
            load_searching_results(task_id);
        }

    }).fail(function (jqXHR, textStatus, errorThrown) {
        reset_timer();
        log_log('ERROR:check_task_searching_status->get_task_status->' + textStatus + ' ' + errorThrown);
        handleRequestError();
    });

}

function get_models() {
    return $.get(ApiUrl.get_models);
}

function get_additives() {
    return $.get(ApiUrl.get_additives);
}

function __get_prepare_task() {
    log_log('get_prepare_task->');
    task_id = get_task();

    if (task_id == "") {
        alert('Session task not defined');
        return false;
    }

    hide_all();

    $.get(ApiUrl.prepare_task + task_id).done(function (resp, textStatus, jqXHR) {

        log_log('prepare_task->done:' + textStatus);
        Progress.done();

        $.when(
            get_models(),
            get_additives()
        ).then(function (models_data, additives_data) {
            var models = models_data[0];
            var additives = additives_data[0];
            display_task_reactions(resp.structures, models, additives);
        });

    }).fail(function (jqXHR, textStatus, errorThrown) {
        log_log('prepare_task->' + textStatus)
    });

    return true;
}

function get_prepare_task() {
    log_log('get_prepare_task->');
    task_id = get_task();

    if (task_id == "") {
        alert('Session task not defined');
        return false;
    }

    hide_all();

    $.get(ApiUrl.prepare_task + task_id).done(function (resp, textStatus, jqXHR) {

        log_log('prepare_task->done:' + textStatus);
        Progress.done();


        display_reactions_prepare_task(resp.structures);

    }).fail(function (jqXHR, textStatus, errorThrown) {
        log_log('prepare_task->' + textStatus)
    });

    return true;
}

function post_prepare_task(structure_data)
{
    log_log('post_prepare_task->');
    var task_id = get_task();
    if (task_id == "") {
        alert('Session task not defined');
        return false;
    }

    var data = [];

    $("#prepare-reactions-tbd input:hidden[data-is-changed='1']").each(function () {
        var structure_id = this.getAttribute('data-structure-id');
        var structure_data = decodeURIComponent(this.value);
        data.push({structure: structure_id, data:structure_data});
    });

    data = JSON.stringify(data);
    log_log(data);
    $.ajax({
        "url": ApiUrl.prepare_task+task_id
        , "type": "POST"
        , "dataType": "json"
        , "contentType": "application/json"
        , "data": data
    }).done(function (resp, textStatus, jqXHR) {
        log_log(resp);
        var task_id = resp.task;
        set_task(task_id);
        start_prepare_model_task(task_id);

    }).fail(function(){});

}


function clear_editor() {
    try {
        marvinSketcherInstance.clear();
    }
    catch (err) {
        log_log(err)
    }
}

function display_reactions_prepare_task(reactions) {

    log_log('display_reactions_prepare_task->');
    log_log(reactions)

    // если скрыт редактор - покажем его
    show_editor();

    // очистим редактор
    //clear_editor();

    //  resize editor
    $("#editor-div").parent().removeClass("col-md-12").addClass("col-md-6");

    var jTbl = $("#prepare-reactions-tbd");
    jTbl.empty();
    var str = '';
    var reaction_ids = '';
    var first_reaction_id = '';

    for (var i = 0; i < reactions.length; i++) {
        var _reaction = reactions[i];
        var _r_id = _reaction.structure;
        if (i == 0)
            first_reaction_id = _r_id;

        str += '<tr  data-structure-id="' + _r_id + '">';

        str += '<td>';
        str += '<input type="hidden" id="structure_data'+_r_id+'"  name="structure_data'+_r_id+'" class=""  value="'+encodeURIComponent(_reaction.data)+'" data-is-changed="0" data-structure-id="' + _r_id + '" >';
        str += '<a href="#"><img class="structure-img"   width="150" height="100" border="0" data-structure-id="' + _r_id + '" ></a>';
        str += '</td>';

        str += '<td>' + get_status_name(StructureStatus,_reaction.status) + '</td>';

        str += '<td>';
        str += '<button class="btn btn-danger" data-structure-id="' + _r_id + '"  data-role="todelete-btn" >Delete</button>';
        str += '<input  type="hidden" data-role="todelete" name="todelete'+_r_id+'" value="0">';
        str += '</td>';
        str += '</tr>';

    }

    jTbl.append(str);


    var settings = {
        'carbonLabelVisible': false,
        'cpkColoring': true,
        'implicitHydrogen': false,
        'width': 150,
        'height': 100,
        'zoomMode': 'autoshrink'
    };

    jTbl.find("img.structure-img").each(function () {
        var $img = $(this);
        var _id = $img.attr("data-structure-id");
        var data = decodeURIComponent($("#structure_data"+_id).val());
        var dataUrl = marvin.ImageExporter.mrvToDataUrl(data, "image/png", settings);
        $img.attr('src', dataUrl);
    });

    $("#prepare-reactions-div").show("normal");

    /*********** Add reaction save button to the editor ***************/
    var jso = {
        "name": "saveButton", // JS String
        "image-url": "/static/images/save.png", // JS String */
        "toolbar": "S" // JS String: "W" as West, "E" as East, "N" as North, "S" as South toolbar

    }

    // проверим - не были ли уже добавлена кнопка
    if (!isSaveMrvBtnExists) {
        // добавили кнопку под редактором
        //marvinSketcherInstance.addButton(jso, save_structure_from_editor );
        isSaveMrvBtnExists = true;
    }

    /*
     if(first_reaction_id!='')
     load_reaction(first_reaction_id);
     */

}


function display_reactions_model_task(reactions, models, additives) {

    //log_log('display_task_reactions->');

    // если скрыт редактор - покажем его
    show_editor();

    // очистим редактор
    //clear_editor();

    //  resize editor
    $("#editor-div").parent().removeClass("col-md-12").addClass("col-md-6");

    var jTbl = $("#reactions-tbd");
    jTbl.empty();
    var str = '';
    var reaction_ids = '';
    var first_reaction_id = '';
    var _temperature = '';
    var _status = '';
    var _solvent_id = '';
    var reaction_models = [];
    var reaction_model_ids = '';

    for (var i = 0; i < reactions.length; i++) {
        var _reaction = reactions[i];
        var _r_id = _reaction.structure;
        if (i == 0)
            first_reaction_id = _r_id;
        try {
            _temperature = _reaction.temperature;
            if (isEmpty(_temperature))
                _temperature = '';
        } catch (err) {
        }

        try {
            _status = _reaction.status;
            if (isEmpty(_status))
                _status = '';
        } catch (err) {
        }

        try {
            reaction_models = _reaction.models;
        }
        catch (err) {
            _reaction_models = []
        }

        try {
            reaction_additives = _reaction.additives;
        }
        catch (err) {
            reaction_additives = []
        }

        str += '<tr  data-structure-id="' + _r_id + '"  data-is-changed="0">';
        str += '<input type="text" name="structure_data'+_r_id+'" value="'+encodeURIComponent(_reaction.data)+'">';
        str += '<td><a href="#"><img class="structure-img"   width="150" height="100" border="0" data-structure-id="' + _r_id + '" ></a></td>';
        str += '<td>';

        str += '<select  multiple="multiple" data-role="model" name="model_' + _r_id + '" id="model_' + _r_id + '">';
        //str+='<option value=""></option>';
        try {
            for (var j = 0; j < models.length; j++) {
                _m = models[j];
                var _s = '';
                if (find(reaction_models, _m.model, 'model') >= 0)
                    _s = 'selected';

                str += '<option ' + _s + ' value="' + _m.model + '">' + _m.name + '</option>';
            }
        }
        catch (err) {
            log_log(err)
        }
        str += '</select>';
        str += '</td>';


        str += '<td>';

        str += '<ul class="nav" role="navigation">\
            <li class="dropdown"> <a href="#" role="button" class="dropdown-toggle btn btn-default" data-toggle="dropdown">Select</a>\
                <ul class="dropdown-menu" role="menu">';
                for (var si=0;si<additives.length;si++)
                {
                    var add = additives[si];
                    str+='<li data-additive-name="'+add.name+'"><a role="menuitem" tabindex="-1" href="#"><div>'+add.name+'  <input data-additive-id="'+add.additive+'" type="text" class="addivitve-amount" id="additive_amount'+si+'" placeholder=""/></div></a></li>';
                }
        str+='\
                </ul>\
            </li>\
        </ul>';

        str += '</td>';


        str += '<td><input  class="form-control" data-role="temperature" name="temperature_' + _r_id + '" type="text" value="' + _temperature + '" size="5"/></td>';
        str += '<td>' + _status + '</td>';
        str += '</tr>';

        if (reaction_ids == '')
            reaction_ids += _r_id;
        else
            reaction_ids += ',' + _r_id;
    }
    jTbl.append(str);




    var settings = {
        'carbonLabelVisible': false,
        'cpkColoring': true,
        'implicitHydrogen': false,
        'width': 150,
        'height': 100,
        'zoomMode': 'autoshrink'
    };

    jTbl.find("img.structure-img").each(function () {
        var $img = $(this);
        var data = decodeURIComponent($img.attr("data-structure"));
        var dataUrl = marvin.ImageExporter.mrvToDataUrl(data, "image/png", settings);
        $img.attr('src', dataUrl);
    });


    $('#task_reaction_ids').val(reaction_ids);


    $("#reactions-div").show("normal");

    /*********** Add reaction save button to the editor ***************/
    var jso = {
        "name": "saveButton", // JS String
        "image-url": "/static/images/save.png", // JS String */
        "toolbar": "S" // JS String: "W" as West, "E" as East, "N" as North, "S" as South toolbar

    }

    // проверим - не были ли уже добавлена кнопка
    if (!isSaveMrvBtnExists) {
        // добавили кнопку под редактором
        //marvinSketcherInstance.addButton(jso, save_structure_from_editor );
        isSaveMrvBtnExists = true;
    }

    /*
     if(first_reaction_id!='')
     load_reaction(first_reaction_id);
     */

    // загрузим модели в шапку
    try {
        var str = '';
        for (var i = 0; i < models.length; i++) {
            var _id = models[i].model;
            var _name = models[i].name;
            str += '<option value="' + _id + '">' + _name + '</option>';
        }

        var jSelect = $("#model_selector");
        jSelect.append(str);

        jSelect.multiselect({
            buttonText: function (options, select) {
                return 'Model';
            },
            buttonTitle: function (options, select) {
                return 'Model';
            },
            onChange: function (option, checked, select) {
                var _val = $(option).val();
                var jTbl = $("#reactions-tbd");
                try {
                    jTbl.find('select[role=model]').each(function () {
                        var jSelect = $(this);
                        if (checked)
                            jSelect.find('option[value="' + _val + '"]').attr('selected', 'selected');
                        else
                            jSelect.find('option[value="' + _val + '"]').removeAttr('selected');
                        jSelect.multiselect('refresh');
                    })
                }
                catch (err) {
                    log_log(err)
                }


            }
        });
    }
    catch (err) {
        log_log('display_task_reactions->load models->' + err)
    }

    try {
        jTbl.find('select[role=model]').each(function () {
            var jSelect = $(this);
            jSelect.multiselect();
        });
    }
    catch (err) {
    }


}



function draw_moldata(data) {
    try {

        marvinSketcherInstance.importStructure(MOL_FORMAT, data).then(function (obj) {


        }, function (error) {
            alert("Molecule export failed:" + error);
        });
        // сбросим флаг изменений в редакторе и скроем кнопку - Сохранить
        //isSketcherDataChanged = false;
        //hide_upload_sketcher_data_btn();

    }
    catch (err) {
        log_log('draw_moldata->');
        log_log(err);
    }
}

function save_structure_from_editor() {
    marvinSketcherInstance.exportStructure(MOL_FORMAT).then(function (source) {

        if (isMolEmpty(source)) {
            alert('You need enter a reaction');
            return false;
        }
        else
        {
            hide_save_sketcher_data_btn();
            set_structure_data(source);
        }


    }, function (error) {
        alert("Molecule export failed:" + error);
    });

}


function post_modeling_task() {
    if (isSketcherDataChanged) {
        if (!confirm('Reactions  in the editor has been changed. To save changes please click the button below editor.Continue without saving?')) {
            return false;
        }

    }
    Progress.start();
    //log_log('post_modeling_task->');
    var task_id = $("#task_id").val();
    if (isEmpty(task_id)) {
        alert('Session task not defined');
        Progress.done();
        return false;
    }
    var data = {};
    $("#reactions-tbd tr").each(function () {

    });

    $("#reactions-form").serializeArray().map(function (x) {
        if (data[x.name])
            data[x.name] = data[x.name] + ',' + x.value;
        else
            data[x.name] = x.value;
    });

    return $.post(ApiUrl.model_task+ task_id, data).done(function (resp, textStatus, jqXHR) {

        // new job will be returned
        var task_id = resp.task;
        set_task(task_id);
        start_modelling();

    }).fail(function (jqXHR, textStatus, errorThrown) {  });
}

function start_modelling() {
    //log_log('start_modelling->');

    TAMER_ID = setInterval(function () {
            get_modeling_result();
        }, TIMER_INTERVAL);

}

function get_modeling_result() {

    //log_log('get_modeling_result->');
    var task_id = get_task();

    if (task_id == "") {
        alert('Session task not defined');
        return false;
    }

    $.get(ApiUrl.model_task + task_id).done(function (data, textStatus, jqXHR) {

        Progress.done();
        display_modelling_results(data);

    }).fail(function (jqXHR, textStatus, errorThrown) {
        log_log('ERROR:get_modeling_result->' + textStatus + ' ' + errorThrown);
    });
    return true;
}

function load_searching_results(task_id) {
    // сбросим таймер - если функцию вызвали из левого меню
    reset_timer();

    if (!task_id)
        task_id = get_task();

    if (task_id == "") {
        alert('Session task not defined');
        return false;
    }

    $.get(API_BASE + "/task_modelling/" + task_id).done(function (data, textStatus, jqXHR) {

        Progress.done();
        try {
            display_searching_results(data);
        }
        catch (err) {
            log_log(err)
        }

    }).fail(function (jqXHR, textStatus, errorThrown) {
        log_log('ERROR:load_searching_results->' + textStatus + ' ' + errorThrown)
    });
    return true;
}


/*** DEBUG ***/



// данные для структур в результатах моделирования
var result_structures = {};
var mrv_result_structures = {};
var reaction_structures = {};

function display_modelling_results(results) {
    //log_log('display_modelling_results->');
    // скроем редактор
    hide_editor();
    // скроем таблицу с реакциями
    hide_reactions();

    var jTbl = $("#results-tbody");
    jTbl.empty();
    var tbd = jTbl.get(0);

    /************************************/
    for (var i = 0; i < results.length; i++) {

        var result = results[i];

        // ID реакции
        r_id = result.reaction_id;

        // результаты моделирования конкретной реакции
        var reaction_results = result.results;

        if (reaction_results.length == 0) {
            reaction_results = [{reaction_id: 0, model: 'unmodelable structure', param: ' ', value: '', type: 0}];
        }

        var rowReaction = tbd.insertRow();

        var cellReactionImg = rowReaction.insertCell();
        cellReactionImg.innerHTML = '<img width="300" class="reaction_img" reaction_id="' + r_id + '" src="{{ url_for("static", filename="images/ajax-loader-tiny.gif") }}"  alt="Image unavailable"/>';
        if (reaction_results.length > 1)
            cellReactionImg.rowSpan = reaction_results.length;

        var solvents = result.solvents;
        try {
            var _arr = new Array();
            for (var j = 0; j < solvents.length; j++)
                _arr.push(solvents[j].name);
            solvents = _arr.join(', ');
        }
        catch (err) {
            solvents = '';
        }

        var cellSolvents = rowReaction.insertCell();
        cellSolvents.innerHTML = solvents;
        if (reaction_results.length > 1)
            cellSolvents.rowSpan = reaction_results.length;

        var temperature = result.temperature;
        if (String(temperature) == "null")
            temperature = "";

        var cellTemperature = rowReaction.insertCell();
        cellTemperature.innerHTML = temperature;
        if (reaction_results.length > 1)
            cellTemperature.rowSpan = reaction_results.length;

        // сгруппируем по моделям
        var models = array_distinct(reaction_results, 'model');
        for (var m = 0; m < models.length; m++) {
            var model_results = array_select(reaction_results, 'model', models[m]);

            if (m > 0)
                rowReaction = tbd.insertRow();

            var cellModel = rowReaction.insertCell();
            cellModel.innerHTML = models[m];
            if (model_results.length > 1)
                cellModel.rowSpan = model_results.length;

            for (var r = 0; r < model_results.length; r++) {
                if (r > 0)
                    rowReaction = tbd.insertRow();

                var _res = model_results[r];

                var cellParam = rowReaction.insertCell();
                cellParam.innerHTML = _res.param;

                var value = '';
                switch (String(_res.type)) {
                    case '0': // текст
                        value = _res.value;
                        break;
                    case '1': // структура
                        var img_id = 'result_structure_img_' + i + '_' + m + '_' + r;
                        result_structures[img_id] = _res.value;
                        value = '<img  id="' + img_id + '" src="{{ url_for("static", filename="images/ajax-loader-tiny.gif") }}" alt="Image unavailable" class="result-structure" />';
                        break;
                    case '2': // ссылка
                        value = '<a href="' + _res.value + '">Open</a>';
                        break;
                    default:
                        value = _res.value;
                        break;
                }

                var cellValue = rowReaction.insertCell();
                cellValue.innerHTML = value;


            }

        }

    }


    var large_settings = {
        'carbonLabelVisible': false,
        'cpkColoring': true,
        'implicitHydrogen': false,
        'width': 600,
        'height': 300
    };


    $("#results-div").show("normal");
    jTbl.find('.reaction_img').each(function () {

        var jImg = $(this);
        if (jImg.attr('reaction_id')) {
            var reaction_id = jImg.attr('reaction_id');
            get_reaction_structure(reaction_id).done(function (data, textStatus, jqXHR) {

                var settings = {
                    'carbonLabelVisible': false,
                    'cpkColoring': true,
                    'implicitHydrogen': false,
                    'width': 300,
                    'height': 100,
                    'zoomMode': 'autoshrink'
                };
                try {
                    reaction_structures[reaction_id] = data;
                    var dataUrl = marvin.ImageExporter.mrvToDataUrl(data, "image/png", settings);
                    jImg.attr('src', dataUrl);
                    jImg.click(function () {
                        var reaction_id = $(this).attr('reaction_id');
                        var data = reaction_structures[reaction_id];
                        var dataUrl = marvin.ImageExporter.mrvToDataUrl(data, "image/png", large_settings);
                        $('#modal-img').attr('src', dataUrl);
                        $('#openModal').show();

                    });
                }
                catch (err) {
                    log_log(err);
                }
            });
        }


    });

    var small_settings = {
        'carbonLabelVisible': false,
        'cpkColoring': true,
        'implicitHydrogen': false,
        'width': 200,
        'height': 100
    };

    // сначала загрузим маленькие картинки и сохраним конвертированные в mrv данные

    jTbl.find('img.result-structure').each(function () {
        try {
            var jImg = $(this);
            var img_id = this.id;
            var data = result_structures[img_id];
            reactionToMrv(data).done(function (result, textStatus, jqXHR) {
                var dataUrl = marvin.ImageExporter.mrvToDataUrl(result, "image/png", small_settings);
                jImg.attr('src', dataUrl);
                mrv_result_structures [img_id] = result;
            });
        }
        catch (err) {
            log_log(err);
        }
    });
    // на клик по картинке посадим загрузку в модальное окно большой картинки
    jTbl.find('img.result-structure').each(function () {
        try {
            var jImg = $(this);
            jImg.click(function () {
                // при клике откроем большую картинку
                $('#openModal').show();
                var data = mrv_result_structures[this.id];
                var dataUrl = marvin.ImageExporter.mrvToDataUrl(data, "image/png", large_settings);
                $('#modal-img').attr('src', dataUrl);
            });
        }
        catch (err) {
            log_log(err);
        }
    });

}

function display_searching_results(results) {
    //log_log('display_searching_results->');
    // скроем редактор
    hide_editor();
    // скроем таблицу с реакциями
    hide_reactions();

    var jTbl = $("#results-tbody");
    jTbl.empty();
    var tbd = jTbl.get(0);

    /************************************/
    for (var i = 0; i < results.length; i++) {

        var result = results[i];

        // ID реакции
        r_id = result.reaction_id;

        // результаты моделирования конкретной реакции
        var reaction_results = result.results;

        if (reaction_results.length == 0) {
            reaction_results = [{reaction_id: 0, param: ' ', value: '', type: 0}];
        }

        var rowReaction = tbd.insertRow();

        var cellReactionImg = rowReaction.insertCell();
        cellReactionImg.innerHTML = '<img width="300" class="reaction_img" reaction_id="' + r_id + '" src="{{ url_for("static", filename="images/ajax-loader-tiny.gif") }}"  alt="Image unavailable"/>';


        // сгруппируем по моделям
        var models = array_distinct(reaction_results, 'model');
        for (var m = 0; m < models.length; m++) {
            var model_results = array_select(reaction_results, 'model', models[m]);

            if (m > 0)
                rowReaction = tbd.insertRow();

            if (model_results.length > 1)
                cellModel.rowSpan = model_results.length;

            for (var r = 0; r < model_results.length; r++) {
                if (r > 0)
                    rowReaction = tbd.insertRow();

                var _res = model_results[r];

                var cellParam = rowReaction.insertCell();
                cellParam.innerHTML = _res.param;

                var value = '';
                switch (String(_res.type)) {
                    case '0': // текст
                        value = _res.value;
                        break;
                    case '1': // структура
                        var img_id = 'result_structure_img_' + i + '_' + m + '_' + r;
                        result_structures[img_id] = _res.value;
                        value = '<img  id="' + img_id + '" src="{{ url_for("static", filename="images/ajax-loader-tiny.gif") }}" alt="Image unavailable" class="result-structure" />';
                        break;
                    case '2': // ссылка
                        value = '<a href="' + _res.value + '">Open</a>';
                        break;
                    default:
                        value = _res.value;
                        break;
                }

                var cellValue = rowReaction.insertCell();
                cellValue.innerHTML = value;


            }

        }

    }


    var large_settings = {
        'carbonLabelVisible': false,
        'cpkColoring': true,
        'implicitHydrogen': false,
        'width': 600,
        'height': 300
    };


    $("#results-div").show("normal");
    jTbl.find('.reaction_img').each(function () {

        var jImg = $(this);
        if (jImg.attr('reaction_id')) {
            var reaction_id = jImg.attr('reaction_id');
            get_reaction_structure(reaction_id).done(function (data, textStatus, jqXHR) {

                var settings = {
                    'carbonLabelVisible': false,
                    'cpkColoring': true,
                    'implicitHydrogen': false,
                    'width': 300,
                    'height': 100
                };
                try {
                    reaction_structures[reaction_id] = data;
                    var dataUrl = marvin.ImageExporter.mrvToDataUrl(data, "image/png", settings);
                    jImg.attr('src', dataUrl);
                    jImg.click(function () {
                        var reaction_id = $(this).attr('reaction_id');
                        var data = reaction_structures[reaction_id];
                        var dataUrl = marvin.ImageExporter.mrvToDataUrl(data, "image/png", large_settings);
                        $('#modal-img').attr('src', dataUrl);
                        $('#openModal').show();

                    });
                }
                catch (err) {
                    log_log(err);
                }
            });
        }


    });

    var small_settings = {
        'carbonLabelVisible': false,
        'cpkColoring': true,
        'implicitHydrogen': false,
        'width': 200,
        'height': 100
    };

    // сначала загрузим маленькие картинки и сохраним конвертированные в mrv данные

    jTbl.find('img.result-structure').each(function () {
        try {
            var jImg = $(this);
            var img_id = this.id;
            var data = result_structures[img_id];
            reactionToMrv(data).done(function (result, textStatus, jqXHR) {
                var dataUrl = marvin.ImageExporter.mrvToDataUrl(result, "image/png", small_settings);
                jImg.attr('src', dataUrl);
                mrv_result_structures [img_id] = result;
            });
        }
        catch (err) {
            log_log(err);
        }
    });
    // на клик по картинке посадим загрузку в модальное окно большой картинки
    jTbl.find('img.result-structure').each(function () {
        try {
            var jImg = $(this);
            jImg.click(function () {
                // при клике откроем большую картинку
                $('#openModal').show();
                var data = mrv_result_structures[this.id];
                var dataUrl = marvin.ImageExporter.mrvToDataUrl(data, "image/png", large_settings);
                $('#modal-img').attr('src', dataUrl);
            });
        }
        catch (err) {
            log_log(err);
        }
    });

}


function load_task(task_id) {
    hide_all();
    // установим задачу
    set_task(task_id);

    // узнаем статус задачи
    get_task_status(task_id).done(function (data, textStatus, jqXHR) {

        switch (data) {
            case MAPPING_DONE:
                reset_timer();
                get_prepare_task(task_id);
                break;

            case MODELLING_DONE:
                reset_timer();
                get_modeling_result(task_id);
                break;
            default:
                load_reactions();
                break;

        }

    }).fail(function (jqXHR, textStatus, errorThrown) {
        reset_timer();
        log_log('ERROR:check_task_mapping_status->get_task_status->' + textStatus + ' ' + errorThrown);
        handleRequestError();
    });
}

function load_model_example(model_id) {
    get_model(model_id).done(function (model, textStatus, jqXHR) {

        Progress.done();
        try {
            hide_select_mode();
            draw_moldata(model.example);
            show_editor(true);
        }
        catch (err) {
            log_log(err)
        }

    }).fail(function (jqXHR, textStatus, errorThrown) {
        log_log('ERROR:load_model_example->' + textStatus + ' ' + errorThrown)
    });
    return true;
}

