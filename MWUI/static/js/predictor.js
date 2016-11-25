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

function array_sum(arr, fld)
{
    var sum = 0;
    for (var i=0;i<arr.length;i++)
    {
        if (fld!=undefined)
            sum+=arr[i][fld];
        else
            sum+=arr[i];
    }
    return sum;
}

function reset_timer() {
    try{
        clearInterval(TAMER_ID);
    }
    catch(err){}

}

function log(str) {
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
        log('find->' + err);
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
    update_structure_image(document.getElementById("structure-img"+structure_id));

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

    //log('increase_progress->');
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
        log(err);
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


function upload_task_file_data() {
    //log('upload_task_file_data->');
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

    $("#prepare-reactions-tbd,#model-reactions-tbd").on('click', 'button[data-role="todelete-btn"]', function () {
        var _id = this.getAttribute("data-structure-id");
        $("#todelete"+_id).val(1);
        $("#structure_data"+_id).attr('data-is-changed','1');
        $(this).closest('tr').addClass('delete-structure-tr');
        return false;

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
    //log('set_task_status->'+status);
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
    //log('get_task_status->'+task_id);
    return $.get(API_BASE + "/task_status/" + task_id);
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

/******* Hide/Show function ******/

function hide_all() {
    hide_select_mode();
    hide_editor();
    hide_reactions();
    hide_file_upload();
    hide_modelling_results();

    hide_prepare_reactions();
    hide_model_reactions();

}

function hide_prepare_reactions()
{
    $("#prepare-reactions-div").hide();
}
function hide_model_reactions()
{
    $("#model-reactions-div").hide();
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

function show_prepare_reactions()
{
    $("#prepare-reactions-div").show();
}
function show_model_reactions()
{
    $("#model-reactions-div").show();
}

function hide_editor() {
    //$('#editor-div').hide();
    $('#sketch').removeClass('sketcher-frame').addClass('hidden-sketcher-frame');
    $("#editor-div").removeClass("resizable")
    hide_upload_sketcher_data_btn();
    hide_save_sketcher_data_btn();
}

function show_editor(show_upload_reaction_button) {
    //$('#editor-div').show(1000);
    $('#sketch').removeClass('hidden-sketcher-frame').addClass('sketcher-frame');
    $("#editor-div").addClass("resizable")
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


/*************************************/

/********** Get/Post functions  ******/

function post_prepare_task(data)
{
    log('upload_data_for_prepare_task->');
    var task_id = get_task();
    if (task_id == "") {
        alert('Session task not defined');
        return false;
    }

    return     $.ajax({
        "url": ApiUrl.prepare_task+task_id
        , "type": "POST"
        , "dataType": "json"
        , "contentType": "application/json"
        , "data": data
    });
}

function post_new_model_task(data)
{
   return     $.ajax({
        "url": ApiUrl.create_model_task
        , "type": "POST"
        , "dataType": "json"
        , "contentType": "application/json"
        , "data": data
    })
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

function get_prepare_task()
{
    var task_id = get_task();

    if (task_id == "") {
        alert('Session task not defined');
        return false;
    }

    return $.get(ApiUrl.prepare_task + task_id);

}

function get_models() {
    return $.get(ApiUrl.get_models);
}

function get_additives() {
    return $.get(ApiUrl.get_additives);
}
/*************************************/


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


function create_model_task(draw_data) {
    //log('create_model_task->');
    hide_upload_sketcher_data_btn();
    hide_save_sketcher_data_btn();

    //var data = {"structures":[{"data":draw_data}]};
    var data = {"data": draw_data};
    data = JSON.stringify(data);

    post_new_model_task(data).done(function (resp, textStatus, jqXHR) {

        log('задача создана:');
        log(resp);
        var task_id = resp.task;
        set_task(task_id);
        start_prepare_model_task(task_id);

    }).fail(handleRequestError);
}

function start_prepare_model_task(task_id) {
    //log('start_prepare_model_task->');
    TAMER_ID = setInterval(function () {
        load_prepare_task(task_id)
    }, TIMER_INTERVAL);

}

function load_data_for_modeling() {
    log('load_data_for_modeling->');

    hide_all();
    Progress.start();

    get_prepare_task().done(function (resp, textStatus, jqXHR) {

        log('prepare_task->done:' + textStatus);
        Progress.done();

        $.when(
            get_models(),
            get_additives()
        ).then(function (models_data, additives_data) {
            var models = models_data[0];
            var additives = additives_data[0];
            display_reactions_for_modeling(resp.structures, models, additives);
        });

    }).fail(function (jqXHR, textStatus, errorThrown) {

        switch(jqXHR.status)
        {
            case 512:
                // task not ready
                break;
            default:
                var msg = JSON.parse(jqXHR.responseText);
                alert(msg.message);
                handleRequestError();

        }
    });

    return true;
}

function load_prepare_task() {

    hide_all();

    get_prepare_task().done(function (resp, textStatus, jqXHR) {

        log('prepare_task->done:' + textStatus);
        Progress.done();

        display_reactions_prepare_task(resp.structures);

    }).fail(function (jqXHR, textStatus, errorThrown) {
        log('prepare_task->' + textStatus)
    });

    return true;
}

function upload_data_for_prepare_task()
{
    Progress.start();
    var data = [];

    $("#prepare-reactions-tbd input:hidden[data-is-changed='1']").each(function () {
        var structure_id = this.getAttribute('data-structure-id');
        var structure_data = decodeURIComponent(this.value);
        var _obj = {structure: structure_id, data:structure_data};
        var todelete = $("#todelete"+structure_id).val();
        if (todelete=="1")
            _obj.todelete = true;

        data.push(_obj);
    });

    data = JSON.stringify(data);

    post_prepare_task(data).done(function (resp, textStatus, jqXHR) {
        log(resp);
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
        log(err)
    }
}

function display_reactions_prepare_task(reactions) {

    log('display_reactions_prepare_task->');
    log(reactions)

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
        str += '<input type="hidden" id="structure_data'+_r_id+'"  name="structure_data'+_r_id+'" value="'+encodeURIComponent(_reaction.data)+'" data-is-changed="0" data-structure-id="' + _r_id + '" >';
        str += '<a href="#"><img class="structure-img" id="structure-img' + _r_id + '"   border="0" data-structure-id="' + _r_id + '" ></a>';
        str += '</td>';

        str += '<td>' + get_status_name(StructureStatus,_reaction.status) + '</td>';

        str += '<td>';
        str += '<button class="btn btn-danger" data-structure-id="' + _r_id + '"  data-role="todelete-btn">Delete</button>';
        str += '<input  type="hidden" data-role="todelete" name="todelete'+_r_id+'" id="todelete'+_r_id+'"  value="0">';
        str += '</td>';
        str += '</tr>';

    }

    jTbl.append(str);




    jTbl.find("img.structure-img").each(function () {
        update_structure_image(this);
    });

    show_prepare_reactions();


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

    for (var i = 0; i < reactions.length; i++)
    {
        if (reactions[i].status!=StructureStatus.CLEAR)
        {
            $("#validate-btn").show();
            break;
        }
    }

    /*
     if(first_reaction_id!='')
     load_reaction(first_reaction_id);
     */

}

function update_structure_image(src)
{
        var settings = {
        'carbonLabelVisible': false,
        'cpkColoring': true,
        'implicitHydrogen': false,
        'width': 300,
        'height': 150,
        'zoomMode': 'autoshrink'
    };

        var $img = $(src);
        var _id = $img.attr("data-structure-id");
        var data = decodeURIComponent($("#structure_data"+_id).val());
        var dataUrl = marvin.ImageExporter.mrvToDataUrl(data, "image/png", settings);
        $img.attr('src', dataUrl);
}

function display_reactions_for_modeling(reactions, models, additives) {

    //log('display_reactions_for_modeling->');

    if (models==undefined)
        models = [];

    if (additives==undefined)
        additives = [];

    var jTbl = $("#model-reactions-tbd");
    jTbl.empty();
    var str = '';

    for (var i = 0; i < reactions.length; i++) {
        var _reaction = reactions[i];
        var _r_id = _reaction.structure;

        var temperature = _reaction.temperature;

        try {
            var reaction_models = _reaction.models;
        }
        catch (err) {
            var eaction_models = []
        }

        try {
            var reaction_additives = _reaction.additives;
        }
        catch (err) {
            var reaction_additives = []
        }

         str += '<tr  data-structure-id="' + _r_id + '">';

        str += '<td>';
        str += '<input type="hidden" id="structure_data'+_r_id+'"  name="structure_data'+_r_id+'" value="'+encodeURIComponent(_reaction.data)+'" data-structure-id="' + _r_id + '" >';
        str += '<a href="#"><img class="structure-img" id="structure-img' + _r_id + '"   border="0" data-structure-id="' + _r_id + '" ></a>';
        str += '</td>';

        str += '<td>';
        str += '<select  multiple="multiple" data-role="model" name="model_' + _r_id + '" id="model_' + _r_id + '">';
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
            log(err)
        }
        str += '</select>';
        str += '</td>';


        str += '<td>';

        str += '<ul class="nav" role="navigation">\
            <li class="dropdown"> <a href="#" role="button" class="dropdown-toggle btn btn-default" data-toggle="dropdown">None selected</a>\
                <ul class="dropdown-menu" role="menu">';
                for (var si=0;si<additives.length;si++)
                {
                    var add = additives[si];
                    str+='<li data-additive-name="'+add.name+'"><a role="menuitem" tabindex="-1" href="#"><div>'+add.name+'  <input data-role="additive-amout" data-additive-id="'+add.additive+'" type="text" class="addivitve-amount" id="additive_amount'+si+'" placeholder=""/></div></a></li>';
                }
        str+='\
                </ul>\
            </li>\
        </ul>';

        str += '</td>';


        str += '<td><input  class="form-control" data-role="temperature" name="temperature_' + _r_id + '" type="text" value="' + temperature + '" size="5"/></td>';
        str += '</tr>';

    }
    jTbl.append(str);

    jTbl.find("img.structure-img").each(function () {
        update_structure_image(this);
    });

    show_model_reactions();


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
                    log(err)
                }


            }
        });
    }
    catch (err) {
        log('display_task_reactions->load models->' + err)
    }

    try {
        jTbl.find('select[data-role=model]').each(function () {
            $(this).multiselect();
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
        log('draw_moldata->');
        log(err);
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

function post_model_task(data)
{
        var task_id = get_task();
        if (task_id=="") {
            alert('Session task not defined');
            Progress.done();
            return false;
        }
        return $.post(ApiUrl.model_task+ task_id, data);
}
function upload_task_for_modeling() {

    //log('upload_task_for_modeling->');

    Progress.start();

    var data = [];
    $("#model-reactions-tbd tr").each(function () {
        var _obj = {};
        var $tr = $(this);

        _obj.structure = $tr.attr("data-structure-id");
        _obj.temperature = $tr.find('input[data-role=temperature]').val();
        _obj.models = $tr.find('select[data-role=model] option:selected').map(function(){return {model:this.value}}).toArray();
        _obj.additives = $tr.find('input[data-role="additive-amout"]').map(function(){if (this.value!='') return {amount:this.value, additive:this.getAttribute('data-additive-id')} }).toArray();

        data.push(_obj);
    });

    log(data);

    return post_model_task(JSON.stringify(data)).done(function (resp, textStatus, jqXHR) {

        // new job will be returned
        var task_id = resp.task;
        set_task(task_id);
        start_modelling();

    }).fail(function (jqXHR, textStatus, errorThrown) {  });
}

function start_modelling() {
    //log('start_modelling->');
    Progress.start();
    TAMER_ID = setInterval(function () {
            get_modeling_result();
        }, TIMER_INTERVAL);

}

function get_modeling_result() {

    //log('get_modeling_result->');
    var task_id = get_task();

    if (task_id == "") {
        alert('Session task not defined');
        return false;
    }

    $.get(ApiUrl.model_task + task_id).done(function (resp, textStatus, jqXHR) {

        Progress.done();

        display_modelling_results(resp.structures);

    }).fail(function (jqXHR, textStatus, errorThrown) {

    });
    return true;
}

/*** DEBUG ***/



// данные для структур в результатах моделирования
var result_structures = {};
var mrv_result_structures = {};
var reaction_structures = {};

function display_modelling_results(structures) {
    //log('display_modelling_results->');

    hide_all();

    // DEBUG
    //structures = [{structure:1, data:"", temperature:300, models:[{model:1, name:"model 1", results:[{key:"param1", value:"value1", type:0}]},{model:2, name:"model 2", results:[{key:"param2", value:"value2", type:0}]}], additives:[{additive:"ethanol", amount:55}, {additive:"water", amount:44}]}]

    var jTbl = $("#results-tbody");
    jTbl.empty();
    var tbd = jTbl.get(0);

    /************************************/
    for (var i = 0; i < structures.length; i++) {


        var structure_span_count = 0;
        var structure_data, additives,temperature, structure, r_id, models,  row, cellReactionImg, cellSolvents, cellTemperature, _model, cellModel, _results, cellModelResultKey, cellModelResultValue, _result;

        structure = structures[i];
        // ID реакции
        r_id = structure.structure;
        structure_data = structure.data;

        models = structure['models'] || [{model:1, name:"unmodelable structure"}];
        temperature = structure['temperature'] | "";
        additives = structure['additives'] || [{additive:0, name:""}];

        $.map(models,function (n,i) {structure_span_count+=n.results.length});
        structure_span_count = structure_span_count || 1;

        row = tbd.insertRow();

        cellReactionImg = row.insertCell();
        cellReactionImg.innerHTML = '<input type="hidden" id="structure_data'+r_id+'"  name="structure_data'+r_id+'" value="'+encodeURIComponent(structure_data)+'" data-structure-id="' + r_id + '" ><a href="#"><img class="structure-img" id="structure-img' + r_id + '"   border="0" data-structure-id="' + r_id + '" ></a>';

        cellReactionImg.rowSpan = structure_span_count;

        cellSolvents = row.insertCell();
        cellSolvents.innerHTML = $.map(additives,function (n,i) {return n.additive+" ("+n.amount+")"}).join(', ');
        cellSolvents.rowSpan = structure_span_count;

        cellTemperature = row.insertCell();
        cellTemperature.innerHTML = temperature;
        cellTemperature.rowSpan = structure_span_count;

        for(var mi=0;mi<models.length;mi++)
        {
            _model = models[mi];
            _results = _model['results'] || [{key:"", value:""}];
            if (mi>0)
            {
                row = tbd.insertRow();
            }
            cellModel = row.insertCell();
            cellModel.innerHTML = _model.name;
            cellModel.rowSpan = _results.length;

            for (ri=0;ri<_results.length;ri++)
            {
                _result = _results[ri];
                if (ri>0)
                {
                    row = tbd.insertRow();
                }
                cellModelResultKey = row.insertCell();
                cellModelResultKey.innerHTML = _result.key;

                cellModelResultValue = row.insertCell();
                cellModelResultValue.innerHTML = _result.value;
            }
        }
    }

    $(tbd).find("img.structure-img").each(function () {
        update_structure_image(this);
    });

    $("#results-div").show("normal");
/*

    var large_settings = {
        'carbonLabelVisible': false,
        'cpkColoring': true,
        'implicitHydrogen': false,
        'width': 600,
        'height': 300
    };

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
                    log(err);
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
            log(err);
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
            log(err);
        }
    });
*/
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
        log('ERROR:check_task_mapping_status->get_task_status->' + textStatus + ' ' + errorThrown);
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
            log(err)
        }

    }).fail(function (jqXHR, textStatus, errorThrown) {
        log('ERROR:load_model_example->' + textStatus + ' ' + errorThrown)
    });
    return true;
}


/*** **********       SEARCH    *************/


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

function upload_search_task_draw_data(draw_data) {
    //log('upload_search_task_draw_data->');
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

        //log('TASK_ID = '+data);
        $("#task_id").val(data);
        start_task_searching(data);

    }).fail(handleRequestError);
}

function start_task_searching(task_id) {

    TAMER_ID = setInterval(function () {
        check_searching_task_status(task_id)
    }, TIMER_INTERVAL);

}

function display_searching_results(results) {
    //log('display_searching_results->');
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
                    log(err);
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
            log(err);
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
            log(err);
        }
    });

}

function check_searching_task_status(task_id) {
    //log('check_searching_task_status->');

    get_task_status(task_id).done(function (data, textStatus, jqXHR) {

        if (data == MODELLING_DONE) {
            reset_timer();
            load_searching_results(task_id);
        }

    }).fail(function (jqXHR, textStatus, errorThrown) {
        reset_timer();
        log('ERROR:check_task_searching_status->get_task_status->' + textStatus + ' ' + errorThrown);
        handleRequestError();
    });

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
            log(err)
        }

    }).fail(function (jqXHR, textStatus, errorThrown) {
        log('ERROR:load_searching_results->' + textStatus + ' ' + errorThrown)
    });
    return true;
}

