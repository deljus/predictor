/******************************************************/
TASK_CREATED    = 0
REQ_MAPPING     = 1
LOCK_MAPPING    = 2
MAPPING_DONE    = 3
REQ_MODELLING   = 4
LOCK_MODELLING  = 5
MODELLING_DONE  = 6

var TIMER_INTERVAL = 5000;
var MOL_FORMAT = 'mrv';

var TAMER_ID;

var marvinSketcherInstance;
var isSaveMrvBtnExists=false;

var isSketcherDataChanged = false;

var API_BASE = '/api';
/******************************************************/

function reset_timer()
{
    clearInterval(TAMER_ID);
}

function log_log(str)
{
	try {
		if (str instanceof Error)
			console.log(str.name + ":" + str.message);
		else
			console.log(str);
	}
	catch (err){}
}


function find(arr, what, where)
{
    var elem = undefined;
    try {
        for (var i=0; i<arr.length;i++)
        {
            elem = arr[i];
            if (where)
                elem = elem[where];
            if (elem==what)
                return i;
        }
    }
    catch(err){
        log_log('find->'+err);
    }
    return -1;
}

/*** debug fuctions ***/
function set_task(task_id)
{
	$('#task_id').val(task_id);	
}
function get_task()
{
	return 	$('#task_id').val();
}
function load_reactions()
{
	hide_all();
	load_task_reactions(get_task());		
}

function load_results()
{
	hide_all();
	load_modelling_results(get_task());		
}

function map_done()
{
	set_task_status(get_task(),MAPPING_DONE)	
}

function model_done()
{
	set_task_status(get_task(),MODELLING_DONE)	
}


var Progress = {}
Progress.increase_progress = function(value){
	
	log_log('increase_progress->');
	try {	
		var jPrg= $('.progress div[role=progressbar]');
		if (value)
			var prc = value;
		else
		{
			var prc = parseInt(jPrg.attr('aria-valuenow'));
			if (prc>=90)
				prc = 0;
				
			prc+=10;				
		}
		

		jPrg.attr('aria-valuenow', prc);
		jPrg.width(prc+'%');//.text(prc+'%');
	}
	catch(err){
		log_log(err);
	}
}

Progress.start = function(){
	$('.progress').show();
	this.timer_id = setInterval(this.increase_progress, 1000);
}

Progress.done = function(){
	clearInterval(this.timer_id);
	this.increase_progress(100);
	setTimeout(function(){$('.progress').hide()}, 1000);	
} 

function handleRequestError()
{
    Progress.done();
}

function download_results(format)
{
	var task_id = $('#task_id').val();
	window.open(API_BASE+'/download/'+task_id+'?format='+format);	
}

function select_mode(mode)
{
	hide_all();
    switch(mode)
    {
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

function upload_file(data)
{
       return  $.ajax({
            type: 'POST',
            url: API_BASE+'/upload',
            data: data,
            contentType: false,
            cache: false,
            processData: false,
            async: false,
        });	
	
}

function upload_task_file_data()
{
	log_log('upload_task_file_data->');
	Progress.start();
			
	var form_data = new FormData($('#upload-file-form')[0]);	
	upload_file(form_data).done(function (data, textStatus, jqXHR) {

		hide_file_upload();
		
        $("#task_id").val(data);
        start_task_mapping(data);

    }).fail(handleRequestError);
}


$(function() {
    $('#upload-file-btn').click(function() {

        if ($('#file').val()=='')
        {
            alert('You have to select file');
            return false;
        }
		upload_task_file_data();
    });
});

function isEmpty(val)
{
    if (val=='' || val==undefined || val=='undefined' || val==null || val=='null')
        return true;
    else
        return false;
}


function reactionToMrv(mol)
{
    var services = getDefaultServices();
    var data = JSON.stringify({"structure": mol});
	return $.ajax({type:'POST',
	        url: services['automapperws'],
	        contentType: 'application/json',
	        data: data
	        });
}

function isMolEmpty(data)
{
    if ( String(data).indexOf('MChemicalStruct')>=0 || String(data).indexOf('$RXN')>=0)
        return false;
    else
        return true;
}

function set_task_status(task_id, status)
{
    log_log('set_task_status->'+status);
    var data =  JSON.stringify({"task_status": status});
    return $.ajax({
        "url": API_BASE+"/task_status/"+task_id
        ,"type": "PUT"
        ,"dataType": "json"
        ,"contentType": "application/json"
        ,"data": data
    });
}

function get_task_status(task_id)
{
	log_log('get_task_status->'+task_id);
    return $.get(API_BASE+"/task_status/"+task_id);
}

function get_reaction_structure(reaction_id)
{
    return $.get(API_BASE+"/reaction_structure/"+reaction_id);
}

function put_reaction_structure(reaction_id, data)
{ 
    log_log('put_reaction_structure->');
    var data = {"reaction_structure": data};

    return $.post(API_BASE+"/reaction_structure/"+reaction_id, data);
}

function get_models(model_hash)
{
    data = {"hash": model_hash};
    return $.get(API_BASE+"/models", data);
}

function get_solvents()
{
    return $.get(API_BASE+"/solvents");
}

function get_reactions_by_task(task_id)
{
    return $.get(API_BASE+"/task_reactions/"+task_id)
}

function get_model(model_id)
{
    return $.get(API_BASE+"/model/"+model_id)
}

function initControl ()
{
	// get mol button
	$("#btn-upload-sketcher-data").on("click", function (e) {
        upload_sketcher_data();
	});
}

function hide_all()
{
	hide_select_mode();
	hide_editor();
	hide_reactions();
	hide_file_upload();
	hide_modelling_results();
	
}

function hide_modelling_results()
{
	$('#results-div').hide();	
}

function hide_select_mode()
{
    $('#select-mode-div').hide(1000);
}
function hide_upload_sketcher_data_btn()
{
	$('#btn-upload-sketcher-data-div').hide();	
}

function show_upload_sketcher_data_btn()
{
	$('#btn-upload-sketcher-data-div').show();
}

function hide_save_sketcher_data_btn()
{
	$('#btn-save-sketcher-data-div').hide();
}

function show_save_sketcher_data_btn()
{
	$('#btn-save-sketcher-data-div').show();
}

function hide_editor()
{
	//$('#editor-div').hide();
	$('#sketch').removeClass('sketcher-frame').addClass('hidden-sketcher-frame');
	hide_upload_sketcher_data_btn();
	hide_save_sketcher_data_btn();
}

function show_editor(show_upload_reaction_button)
{
	//$('#editor-div').show(1000);
	$('#sketch').removeClass('hidden-sketcher-frame').addClass('sketcher-frame');
	if (show_upload_reaction_button)
	{
		show_upload_sketcher_data_btn();
	}

}

function hide_reactions()
{
	$('#reactions-div').hide();	
}

function hide_file_upload()
{
	$('#file-upload-div').hide();	
}

function show_file_upload()
{
	$('#file-upload-div').show(1000);	
}



function upload_sketcher_data()
{
	    Progress.start();
		marvinSketcherInstance.exportStructure(MOL_FORMAT).then(function(source) {


            if (isMolEmpty(source))
            {
                alert('You need enter a reaction');
				Progress.done();
                return false;
            }
            else
                upload_task_draw_data(source);

		}, function(error) {
			alert("Molecule export failed:"+error);
		});
}


function upload_task_draw_data(draw_data)
{
    log_log('upload_task_draw_data->');
	hide_upload_sketcher_data_btn();
	hide_save_sketcher_data_btn();

    var data = JSON.stringify({"reaction_structure": draw_data});

    $.ajax({
            "url": API_BASE+"/tasks"
            ,"type": "POST"
            ,"dataType": "json"
            ,"contentType": "application/json"
            ,"data": data
    }).done(function (data, textStatus, jqXHR) {

		log_log('TASK_ID = '+data);
        $("#task_id").val(data);
        start_task_mapping(data);

    }).fail(handleRequestError);
}

function start_task_mapping(task_id)
{
    log_log('start_task_mapping->');
	/***
    set_task_status(task_id, REQ_MAPPING).done(function (data, textStatus, jqXHR){

        TAMER_ID = setInterval(function(){check_task_mapping_status(task_id)}, TIMER_INTERVAL);

    }).fail(function(jqXHR, textStatus, errorThrown){
		log_log('start_task_mapping->set_task_status->' + textStatus+ ' ' + errorThrown);
		handleRequestError();
	});
	***/
	TAMER_ID = setInterval(function(){check_task_mapping_status(task_id)}, TIMER_INTERVAL);

}

function check_task_mapping_status(task_id)
{
    log_log('check_task_mapping_status->');
	
    get_task_status(task_id).done(function (data, textStatus, jqXHR){

		if (data==MAPPING_DONE)
		{
			reset_timer();
			load_task_reactions(task_id);
		} 

    }).fail(function(jqXHR, textStatus, errorThrown){
        reset_timer();
        log_log('ERROR:check_task_mapping_status->get_task_status->' + textStatus+ ' ' + errorThrown);
        handleRequestError();
    });

}


function load_task_reactions(task_id)
{
    // сбросим таймер - если функцию вызвали из левого меню
    reset_timer();
    log_log('load_task_reactions->');
	if (!task_id)
		task_id = get_task();
		
	if (isNaN(task_id))
	{
		alert('Session task not defined');
		return false;	
	}
	
    get_reactions_by_task(task_id).done(function (data, textStatus, jqXHR){

        Progress.done();

        try {
            display_task_reactions(data);
        }
        catch (err){log_log(err)}

    }).fail(function(jqXHR, textStatus, errorThrown){
        log_log('load_task_reactions->' + textStatus+ ' ' + errorThrown)});
        handleRequestError();
    return true;
}

function clear_editor()
{
    try {
		//marvinSketcherInstance.clear();
	}
	catch(err){log_log(err)}
}

function display_task_reactions(reactions)
{
    log_log('display_task_reactions->');
	
	// если скрыт редактор - покажем его
	show_editor();

	// очистим редактор
	clear_editor();

    var jTbl = $("#reactions-tbd");
    jTbl.empty();
    var str = '';
    var reaction_ids = '';
    var first_reaction_id = '';
    var _temperature = '';
    var _solvent_id = '';
    var models = [];
    for (var i=0;i<reactions.length;i++)
    {
        var _reaction = reactions[i];
        var _r_id = _reaction.reaction_id;
        if (i==0)
            first_reaction_id = _r_id;
        try {
            _temperature = _reaction.temperature;
            if (isEmpty(_temperature))
                _temperature = '';
        }catch(err){}

        try {
            _solvent_id = _reaction.solvents[0].id;
        }catch(err){}

        try {
            models = _reaction.models;
        }
        catch(err){}

        if (models.length==0)
            str+='<tr class="info">';   // если нет моделей - выделим строку
        else
            str+='<tr>';
        str+='<td class="reaction_id" reaction_id="'+_r_id+'"><a href="#">'+(i+1)+'</a></td>';
        str+='<td>';
        str+='<select multiple="multiple" role="model" name="model_'+_r_id+'" id="model_'+_r_id+'">';
        //str+='<option value=""></option>';
        try {
            for (var j=0; j < _reaction.models.length; j++)
            {
                _m = _reaction.models[j];
                var  _s = '';
                if (find(models,_m.id,'id')>=0)
                    _s = 'selected';

                str+='<option '+_s+' value="'+_m.id+'">'+_m.name+'</option>';
            }
        }
        catch(err){log_log(err)}
        str+='</select>';
        str+='</td>';

        str+='<td><select role="solvent" name="solvent_'+_r_id+'" solvent="'+_solvent_id+'" ></select></td>';
        str+='<td><input  class="temperature" name="temperature_'+_r_id+'" type="text" value="'+_temperature+'" /></td>';
        str+='</tr>';

        if (reaction_ids=='')
            reaction_ids+=_r_id;
        else
            reaction_ids+=','+_r_id;
    }
    jTbl.append(str);

    $('#task_reaction_ids').val(reaction_ids);

    jTbl.find(".reaction_id").click(function (){
                                        var r_id = $(this).attr('reaction_id');
                                        load_reaction(r_id);
                                    });

    /*********** Loading models ***************/
    try {
        get_models('').done(function(data, textStatus, jqXHR){

            var str = '';
            for (var i=0; i<data.length; i++)
            {
                var _id = data[i].id;
                var _name = data[i].name;
                str+='<option value="'+_id+'">'+_name+'</option>';
            }

            jTbl.find('select[role=model]').each(function(){
                var jSelect = $(this);
                // если модели еще не были загружены
                if (jSelect.find('option').length==0)
                    jSelect.append(str);

                jSelect.find('option[value='+jSelect.attr('model')+']').attr('selected','selected');
                jSelect.multiselect();
            })
         })
    }
    catch (err){log_log('display_task_reactions->load models->'+err)}

    /*********** Loading solvents ***************/
    try {

        get_solvents().done(function(data, textStatus, jqXHR){

            var str = '<option value=""></option>';
            for (var i=0; i<data.length; i++)
            {
                var _id = data[i].id;
                var _name = data[i].name;
                str+='<option value="'+_id+'">'+_name+'</option>';
            }

            jTbl.find('select[role=solvent]').each(function(){
                var jSelect = $(this);
                jSelect.append(str);
                    if (jSelect.attr('solvent'))
                        jSelect.find('option[value='+jSelect.attr('solvent')+']').attr('selected','selected');

                jSelect.selectpicker();

            })
         })
    }
    catch (err){log_log('display_task_reactions->load models->'+err)}


    $("#reactions-div").show("normal");

    /*********** Add reaction save button to the editor ***************/
    var jso =  {
      "name": "saveButton", // JS String
      "image-url": "/static/images/save.png", // JS String */
      "toolbar": "S" // JS String: "W" as West, "E" as East, "N" as North, "S" as South toolbar

     }

	// проверим - не были ли уже добавлена кнопка
	if (!isSaveMrvBtnExists)
	{
	    // добавили кнопку под редактором
	    //marvinSketcherInstance.addButton(jso, save_draw_reaction );
		isSaveMrvBtnExists=true;
	}

	if(first_reaction_id!='')
	    load_reaction(first_reaction_id);



}

function load_reaction(reaction_id)
{
    log_log('load_reaction->');

    if (isNaN(reaction_id))
    {
        alert('An error occurred when loading the reaction');
        log_log('load_reaction-> reaction_id isNaN:'+reaction_id);
        return false;
    }
	Progress.start();

    get_reaction_structure(reaction_id).done(function (data, textStatus, jqXHR){

        Progress.done();
        $('#reaction_id').val(reaction_id);

        try {
            draw_moldata(data);
        }
        catch (err){log_log(err)}

    }).fail(function(jqXHR, textStatus, errorThrown){log_log('ERROR:show_reaction->' + textStatus+ ' ' + errorThrown)});
    return true;

}

function draw_moldata (data)
{
    try {
        marvinSketcherInstance.importStructure(MOL_FORMAT, data);
        // сбросим флаг изменений в редакторе и скроем кнопку - Сохранить
        //isSketcherDataChanged = false;
        //hide_upload_sketcher_data_btn();

    }
    catch(err){
        log_log('draw_moldata->');
        log_log(err);
    }
}

function save_draw_reaction ()
{
	marvinSketcherInstance.exportStructure(MOL_FORMAT).then(function(source) {

		if (isMolEmpty(source))
		{
			alert('You need enter a reaction');
			return false;
		}
		else
			upload_draw_reaction(source);

	}, function(error) {
		alert("Molecule export failed:"+error);
	});

}

function upload_draw_reaction(data)
{
    log_log('upload_draw_reaction->');
	
	var reaction_id = $('#reaction_id').val();
	if (reaction_id!='')
	{
	    Progress.start();
	    put_reaction_structure(reaction_id,data ).done(function (data, textStatus, jqXHR) {

        Progress.done();
        alert('Reaction has been saved successfully');

    	}).fail(handleRequestError);
	}
	else
	{
        alert('Please, select a reaction from table');
	}
}

function upload_reaction_form()
{
    Progress.start();
    log_log('upload_reaction_form->');
    var task_id = $("#task_id").val();
    if (isEmpty(task_id))
    {
        alert('Session task not defined');
		Progress.done();
        return false;
    }
    var data = {};
	 $("#reactions-form").serializeArray().map(function(x){
		if (data[x.name])
			data[x.name] = data[x.name] +','+ x.value;
		else
			data[x.name] = x.value;
	});

    return $.post(API_BASE+"/task_modelling/"+task_id, data).done(function (data, textStatus, jqXHR){

        start_modelling();

    }).fail(function(jqXHR, textStatus, errorThrown){
        alert('Upload  reactions failure');
		log_log('upload_reaction_forms->' + textStatus+ ' ' + errorThrown);
		handleRequestError();
	});
}

function start_modelling()
{
    log_log('start_modelling->');

    var task_id = $("#task_id").val();
    set_task_status(task_id, REQ_MODELLING).done(function (data, textStatus, jqXHR){

        TAMER_ID = setInterval(function(){check_modelling_status(task_id)}, TIMER_INTERVAL);

    }).fail(function(jqXHR, textStatus, errorThrown){
		log_log('start_modelling->set_task_status->' + textStatus+ ' ' + errorThrown);
		handleRequestError();
	});
}


function check_modelling_status(task_id)
{
    log_log('check_modelling_status->'+task_id);

    get_task_status(task_id).done(function (data, textStatus, jqXHR){

    	if (data==MODELLING_DONE)
		{
			reset_timer();
			load_modelling_results(task_id);
		}

    }).fail(function(jqXHR, textStatus, errorThrown){
        reset_timer();
        log_log('ERROR:check_modelling_status->get_task_status->' + textStatus+ ' ' + errorThrown);
        handleRequestError();
    });

}

function load_modelling_results(task_id)
{
    // сбросим таймер - если функцию вызвали из левого меню
    reset_timer();
    log_log('load_modelling_results->');
	if (!task_id)
		task_id = get_task();
		
	if (isNaN(task_id))
	{
		alert('Session task not defined');
		return false;	
	}	
	
    $.get(API_BASE+"/task_modelling/"+task_id).done(function (data, textStatus, jqXHR){

        Progress.done();
        try {
            display_modelling_results(data);
        }
        catch (err){log_log('load_modelling_results->'+err)}

    }).fail(function(jqXHR, textStatus, errorThrown){log_log('ERROR:load_modelling_results->' + textStatus+ ' ' + errorThrown)});
    return true;
}


function load_reaction_img(reaction_id)
{
    return $.get(API_BASE+"/reaction_img/"+reaction_id);

}
/*** DEBUG ***/



// данные для структур в результатах моделирования
var result_structures = {};
var mrv_result_structures = {};
var reaction_structures = {};

function display_modelling_results(results)
{
	// скроем редактор
	hide_editor();
	// скроем таблицу с реакциями
	hide_reactions();
		
    var jTbl = $("#results-tbody");
    jTbl.empty();
    var str = '';

    var block_count=0;
    var block_class = '';

    for (var i=0;i<results.length; i++)
    {
        var reaction_rowspan=0;
        var result = results[i];
        r_id = result.reaction_id;
        var reaction_results = result.results;
        if (reaction_results.length==0)
        {
            reaction_results = [{reaction_id:0, model:'unmodelable structure', param:' ', value:'', type:0}];
            //reaction_results = [{reaction_id:0, model:'unmodeling data', param:'', value:'', type:0}];
        }

        str+='<tr>';
        str+='<td rowspan="#REACTION_ROWSPAN#"><img width="300" class="reaction_img" reaction_id="'+r_id+'" src="static/images/ajax-loader-tiny.gif"  alt="Image unavailable"/></td>';

        var prev_model = '';
        var modal_rowspan = 0;

        for (var j=0;j<reaction_results.length;j++)
        {
            _res = reaction_results[j];

            switch(_res.param)
            {
                // этот параметр отбрасываем
                case 'TAG':
                    continue;
                break;
            }

            if (j>0)
                str += '<tr class="'+block_class+'" is_block_hide="1">';

            if (prev_model!=_res.model)
            {
                str = str.replace('#MODAL_ROWSPAN#',modal_rowspan);
                str+='<td rowspan=#MODAL_ROWSPAN#>'+_res.model+'</td>';
                prev_model = _res.model;
                modal_rowspan=0;
            }



            str+='<td>'+_res.param+'</td>';
            var value = '';
            switch(String(_res.type))
            {
                case '0': // текст
                    value = _res.value;
                    break;
                case '1': // структура
                    var img_id = 'result_structure_img_'+i+'_'+j;
                    result_structures[img_id] = _res.value;
                    value = '<img  id="'+img_id+'" src="{{ url_for("static", filename="images/ajax-loader-tiny.gif") }}" alt="Image unavailable" class="result-structure" />';
                    break;
                case '2': // ссылка
                    value = '<a href="'+_res.value+'">Open</a>';
                    break;
                default:
                    value = _res.value;
                    break;
            }

            str+='<td>'+value+'</td>';
            str+='</tr>';
            reaction_rowspan++;
            modal_rowspan++;
        }
        str = str.replace('#MODAL_ROWSPAN#',modal_rowspan);
        str = str.replace('#REACTION_ROWSPAN#',reaction_rowspan);
    }

    var large_settings = {
            'carbonLabelVisible' : false,
            'cpkColoring' : true,
            'implicitHydrogen' : false,
            'width' : 600,
            'height' : 300
    };

    jTbl.append(str);


    $("#results-div").show("normal");
    jTbl.find('.reaction_img').each(function(){

        var jImg = $(this);
		if (jImg.attr('reaction_id'))
		{
		    var reaction_id = jImg.attr('reaction_id');
            get_reaction_structure( reaction_id ).done(function(data, textStatus, jqXHR){

                var settings = {
                        'carbonLabelVisible' : false,
                        'cpkColoring' : true,
                        'implicitHydrogen' : false,
                        'width' : 300,
                        'height' : 100
                };
                try {
                    reaction_structures[reaction_id] = data;
                    var dataUrl = marvin.ImageExporter.mrvToDataUrl(data,"image/png",settings);
                    jImg.attr('src',dataUrl);
                    jImg.click(function(){
                        var reaction_id = $(this).attr('reaction_id');
                        var data = reaction_structures[reaction_id];
                        var dataUrl = marvin.ImageExporter.mrvToDataUrl(data,"image/png",large_settings);
                        $('#modal-img').attr('src',dataUrl);
                        $('#openModal').show();

                    });
                }
                catch(err){
                    log_log(err);
                }
            });
		}


    });

    var small_settings = {
            'carbonLabelVisible' : false,
            'cpkColoring' : true,
            'implicitHydrogen' : false,
            'width' : 200,
            'height' : 100
    };

    // сначала загрузим маленькие картинки и сохраним конвертированные в mrv данные

    jTbl.find('img.result-structure').each(function(){
        try {
            var  jImg = $(this);
            var img_id = this.id;
            var data = result_structures[img_id];
            reactionToMrv(data).done(function(result, textStatus, jqXHR){
                var dataUrl = marvin.ImageExporter.mrvToDataUrl(result,"image/png",small_settings);
                jImg.attr('src',dataUrl);
                mrv_result_structures [img_id] = result;
            });
        }
        catch(err){
            log_log(err);
        }
    });
    // на клик по картинке посадим загрузку в модальное окно большой картинки
    jTbl.find('img.result-structure').each(function(){
        try {
            var  jImg = $(this);
            jImg.click(function(){
                // при клике откроем большую картинку
                $('#openModal').show();
                var data = mrv_result_structures[this.id];
                var dataUrl = marvin.ImageExporter.mrvToDataUrl(data,"image/png",large_settings);
                $('#modal-img').attr('src',dataUrl);
            });
        }
        catch(err){
            log_log(err);
        }
    });

}


function load_task(task_id)
{
            hide_all();
            // установим задачу
            set_task(task_id);

            // узнаем статус задачи
            get_task_status(task_id).done(function (data, textStatus, jqXHR){

                switch (data)
                {
                    case MAPPING_DONE:
                        reset_timer();
                        load_task_reactions(task_id);
                        break;

                    case MODELLING_DONE:
		                reset_timer();
			            load_modelling_results(task_id);
			            break;
                    default:
                        load_reactions();
                        break;

                }

            }).fail(function(jqXHR, textStatus, errorThrown){
                reset_timer();
                log_log('ERROR:check_task_mapping_status->get_task_status->' + textStatus+ ' ' + errorThrown);
                handleRequestError();
            });
}

function load_model_example(model_id)
{
    get_model(model_id).done(function (model, textStatus, jqXHR){

        Progress.done();
        try {

            draw_moldata(model.example);
            show_editor(true);
        }
        catch (err){log_log(err)}

    }).fail(function(jqXHR, textStatus, errorThrown){log_log('ERROR:load_model_example->' + textStatus+ ' ' + errorThrown)});
    return true;
}