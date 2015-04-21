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

var API_BASE = '/api';
/******************************************************/

function reset_timer()
{
    clearInterval(TAMER_ID);
}

$(document).ready(function handleDocumentReady (e) {
	initControl();
	MarvinJSUtil.getEditor("#sketch").then(function (sketcherInstance) {
		marvinSketcherInstance = sketcherInstance;
	},function (error) {});
	
	MarvinJSUtil.getPackage("#sketch").then(function (marvinNameSpace) {
		marvinNameSpace.onReady(function () {
			marvin = marvinNameSpace;
		});
	}, function () {
		alert("Cannot retrieve marvin instance from iframe");
	});	

});

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
        console.log('find->'+err);
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
	
	console.log('increase_progress->');
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
		console.log(err);
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
	console.log('upload_task_file_data->');
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
    console.log('set_task_status->'+status);
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
	console.log('get_task_status->'+task_id);
    return $.get(API_BASE+"/task_status/"+task_id);
}

function get_reaction_structure(reaction_id)
{
    return $.get(API_BASE+"/reaction_structure/"+reaction_id);
}

function put_reaction_structure(reaction_id, data)
{ 
    console.log('put_reaction_structure->');
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

function hide_editor()
{
	//$('#editor-div').hide();
	$('#sketch').removeClass('sketcher-frame').addClass('hidden-sketcher-frame');
	$('#btn-upload-sketcher-data-div').hide();
}

function show_editor(show_upload_reaction_button)
{
	//$('#editor-div').show(1000);
	$('#sketch').removeClass('hidden-sketcher-frame').addClass('sketcher-frame');
	if (show_upload_reaction_button)
		$('#btn-upload-sketcher-data-div').show();
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
    console.log('upload_task_draw_data->');
	hide_upload_sketcher_data_btn();

    var data = JSON.stringify({"reaction_structure": draw_data});

    $.ajax({
            "url": API_BASE+"/tasks"
            ,"type": "POST"
            ,"dataType": "json"
            ,"contentType": "application/json"
            ,"data": data
    }).done(function (data, textStatus, jqXHR) {

		console.log('TASK_ID = '+data);
        $("#task_id").val(data);
        start_task_mapping(data);

    }).fail(handleRequestError);
}

function start_task_mapping(task_id)
{
    console.log('start_task_mapping->');
	/***
    set_task_status(task_id, REQ_MAPPING).done(function (data, textStatus, jqXHR){

        TAMER_ID = setInterval(function(){check_task_mapping_status(task_id)}, TIMER_INTERVAL);

    }).fail(function(jqXHR, textStatus, errorThrown){
		console.log('start_task_mapping->set_task_status->' + textStatus+ ' ' + errorThrown);
		handleRequestError();
	});
	***/
	TAMER_ID = setInterval(function(){check_task_mapping_status(task_id)}, TIMER_INTERVAL);

}

function check_task_mapping_status(task_id)
{
    console.log('check_task_mapping_status->');
	
    get_task_status(task_id).done(function (data, textStatus, jqXHR){

		if (data==MAPPING_DONE)
		{
			reset_timer();
			load_task_reactions(task_id);
		} 

    }).fail(function(jqXHR, textStatus, errorThrown){
        reset_timer();
        console.log('ERROR:check_task_mapping_status->get_task_status->' + textStatus+ ' ' + errorThrown);
        handleRequestError();
    });

}


function load_task_reactions(task_id)
{
    // сбросим таймер - если функцию вызвали из левого меню
    reset_timer();
    console.log('load_task_reactions->');
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
        catch (err){console.log(err)}

    }).fail(function(jqXHR, textStatus, errorThrown){
        console.log('load_task_reactions->' + textStatus+ ' ' + errorThrown)});
        handleRequestError();
    return true;
}

function clear_editor()
{
		marvinSketcherInstance.clear();
}

function display_task_reactions(reactions)
{
    console.log('display_task_reactions->');
	
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
        catch(err){console.log(err)}
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
    catch (err){console.log('display_task_reactions->load models->'+err)}

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
    catch (err){console.log('display_task_reactions->load models->'+err)}


    $("#reactions-div").show("normal");

    /*********** Add reaction save button to the editor ***************/
    var jso =  {
      "name": "saveButton", // JS String
      "image-url": "/static/images/save.png", // JS String
      "toolbar": "S" // JS String: "W" as West, "E" as East, "N" as North, "S" as South toolbar
     }

	// проверим - не были ли уже добавлена кнопка
	if (!isSaveMrvBtnExists)
	{
	    marvinSketcherInstance.addButton(jso, save_draw_reaction );
		isSaveMrvBtnExists=true;
	}

	if(first_reaction_id!='')
	    load_reaction(first_reaction_id);

}

function load_reaction(reaction_id)
{
    console.log('load_reaction->');
    if (isNaN(reaction_id))
    {
        alert('An error occurred when loading the reaction');
        console.log('load_reaction-> reaction_id isNaN:'+reaction_id);
        return false;
    }
	Progress.start();

    get_reaction_structure(reaction_id).done(function (data, textStatus, jqXHR){

        Progress.done();
        $('#reaction_id').val(reaction_id);

        try {
            draw_moldata(data);
        }
        catch (err){console.log(err)}

    }).fail(function(jqXHR, textStatus, errorThrown){console.log('ERROR:show_reaction->' + textStatus+ ' ' + errorThrown)});
    return true;

}

function draw_moldata (data)
{
    try {
        marvinSketcherInstance.importStructure(MOL_FORMAT, data);
    }
    catch(err){
        console.log('draw_moldata->'+err)
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
    console.log('upload_draw_reaction->');
	
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
    console.log('upload_reaction_form->');
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
		console.log('upload_reaction_forms->' + textStatus+ ' ' + errorThrown);
		handleRequestError();
	});
}

function start_modelling()
{
    console.log('start_modelling->');

    var task_id = $("#task_id").val();
    set_task_status(task_id, REQ_MODELLING).done(function (data, textStatus, jqXHR){

        TAMER_ID = setInterval(function(){check_modelling_status(task_id)}, TIMER_INTERVAL);

    }).fail(function(jqXHR, textStatus, errorThrown){
		console.log('start_modelling->set_task_status->' + textStatus+ ' ' + errorThrown);
		handleRequestError();
	});
}


function check_modelling_status(task_id)
{
    console.log('check_modelling_status->'+task_id);

    get_task_status(task_id).done(function (data, textStatus, jqXHR){

    	if (data==MODELLING_DONE)
		{
			reset_timer();
			load_modelling_results(task_id);
		}

    }).fail(function(jqXHR, textStatus, errorThrown){
        reset_timer();
        console.log('ERROR:check_modelling_status->get_task_status->' + textStatus+ ' ' + errorThrown);
        handleRequestError();
    });

}

function load_modelling_results(task_id)
{
    // сбросим таймер - если функцию вызвали из левого меню
    reset_timer();
    console.log('load_modelling_results->');
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
        catch (err){console.log('load_modelling_results->'+err)}

    }).fail(function(jqXHR, textStatus, errorThrown){console.log('ERROR:load_modelling_results->' + textStatus+ ' ' + errorThrown)});
    return true;
}


function load_reaction_img(reaction_id)
{
    return $.get(API_BASE+"/reaction_img/"+reaction_id);

}
// данные для структур в результатах моделирования
var result_structures = {};
var mrv_result_structures = {};
var reaction_structures = {}
function display_modelling_results(results)
{
	// скроем редактор
	hide_editor();
	// скроем таблицу с реакциями
	hide_reactions();
		
    var jTbl = $("#results-tbody");
    jTbl.empty();
    var str = '';

reaction1 = "$RXN\n\n  Marvin       041401151653\n\n  1  1\n$MOL\n\n  Mrv0541 04141516532D          \nC12 H16 O3\n 15 15  0  0  0  0            999 V2000\n    5.4141    3.8995    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    4.6994    4.3119    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    6.1286    4.3119    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    5.4141    3.0744    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    3.9851    3.8995    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n    6.8430    3.8995    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    6.1286    2.6618    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    3.2705    4.3119    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    6.8430    3.0744    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    2.5559    3.8995    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    1.8415    4.3119    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    2.5559    3.0744    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    1.1270    3.8995    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n    1.8415    5.1370    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n    0.4123    4.3119    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n  1  2  1  0  0  0  0\n  1  3  4  0  0  0  0\n  1  4  4  0  0  0  0\n  2  5  1  0  0  0  0\n  3  6  4  0  0  0  0\n  4  7  4  0  0  0  0\n  5  8  1  0  0  0  0\n  6  9  4  0  0  0  0\n  7  9  4  0  0  0  0\n  8 10  1  0  0  0  0\n 10 11  1  0  0  0  0\n 10 12  1  0  0  0  0\n 11 13  1  0  0  0  0\n 11 14  2  0  0  0  0\n 13 15  1  0  0  0  0\nM  END\n$MOL\n\n  Mrv0541 04141516532D          \nC5 H10 O3\n  8  7  0  0  0  0            999 V2000\n    9.9221    3.6932    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n   10.6365    4.1055    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    9.2076    4.1055    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    9.9221    2.8680    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n   11.3512    3.6932    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n   10.6365    4.9307    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n    8.4930    3.6932    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n   12.0657    4.1055    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n  1  2  1  0  0  0  0\n  1  3  1  0  0  0  0\n  1  4  1  0  0  0  0\n  2  5  1  0  0  0  0\n  2  6  2  0  0  0  0\n  3  7  1  0  0  0  0\n  5  8  1  0  0  0  0\nM  END"
reaction2 = "$RXN\n\n  Marvin       041401151700\n\n  1  1\n$MOL\n\n  Mrv0541 04141517002D          \nC14 H22 O2\n 17 17  0  0  1  0            999 V2000\n    1.1870    3.2864    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    1.9015    3.6988    0.0000 C   0  0  1  0  0  0  0  0  0  0  0  0\n    1.4008    2.4895    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    0.4125    3.0035    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    0.8389    4.0338    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    2.6160    3.2864    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n    1.9015    4.5238    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    0.8175    1.9053    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n    2.1977    2.2751    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    3.2478    3.8160    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    3.9623    3.4035    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    4.6767    3.8160    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    3.9623    2.5785    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    5.3912    3.4035    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    4.6767    2.1661    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    5.3912    2.5785    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    1.9015    2.8738    0.0000 H   0  0  0  0  0  0  0  0  0  0  0  0\n  1  2  1  0  0  0  0\n  1  3  1  0  0  0  0\n  1  4  1  0  0  0  0\n  1  5  1  0  0  0  0\n  2  6  1  6  0  0  0\n  2  7  1  0  0  0  0\n  3  8  1  0  0  0  0\n  3  9  1  0  0  0  0\n  6 10  1  0  0  0  0\n 10 11  1  0  0  0  0\n 11 12  4  0  0  0  0\n 11 13  4  0  0  0  0\n 12 14  4  0  0  0  0\n 13 15  4  0  0  0  0\n 14 16  4  0  0  0  0\n 15 16  4  0  0  0  0\n  2 17  1  1  0  0  0\nM  END\n$MOL\n\n  Mrv0541 04141517002D          \nC7 H16 O2\n 10  9  0  0  1  0            999 V2000\n    8.4570    3.5708    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    7.8028    3.0681    0.0000 C   0  0  1  0  0  0  0  0  0  0  0  0\n    9.1122    3.0681    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    9.0148    4.1788    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    7.9001    4.1788    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    7.0412    3.3842    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n    7.9108    2.2505    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    9.8745    3.3842    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n    9.0049    2.2505    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n    7.6951    3.8861    0.0000 H   0  0  0  0  0  0  0  0  0  0  0  0\n  1  2  1  0  0  0  0\n  1  3  1  0  0  0  0\n  1  4  1  0  0  0  0\n  1  5  1  0  0  0  0\n  2  6  1  6  0  0  0\n  2  7  1  0  0  0  0\n  3  8  1  0  0  0  0\n  3  9  1  0  0  0  0\n  2 10  1  1  0  0  0\nM  END";

    for (var i=0;i<results.length; i++)
    {
        var result = results[i];
        r_id = result.reaction_id;
        var reaction_results = result.results;
        if (reaction_results.length==0)
        {
            reaction_results = [{reaction_id:0, model:'unmodeling data', param:'1', value:reaction1, type:1},{reaction_id:0, model:'unmodeling data', param:'2', value:reaction2, type:1}];
            //reaction_results = [{reaction_id:0, model:'unmodeling data', param:'', value:'', type:0}];

        }
        str+='<tr>';
        str+='<td rowspan="'+reaction_results.length+'"><img width="300" class="reaction_img" reaction_id="'+r_id+'" src="static/images/ajax-loader-big.gif"  alt="Image unavailable"/></td>';


        var prev_model = '';
        var rowspan = 0;
        for (var j=0;j<reaction_results.length;j++)
        {
            _res = reaction_results[j];
            if (prev_model!=_res.model)
            {
                str = str.replace('#ROWSPAN#',rowspan);
                str+='<td rowspan=#ROWSPAN#>'+_res.model+'</td>';
                prev_model = _res.model;
                rowspan=0;
            }
            rowspan++;

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
                    value = '<img  id="'+img_id+'" src="static/images/ajax-loader-tiny.gif" alt="Image unavailable" class="result-structure" />';
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
        }
        str = str.replace('#ROWSPAN#',rowspan);
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
                    console.log(err);
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
            console.log(err);
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
            console.log(err);
        }
    });

}





