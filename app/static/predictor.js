/**
 * Created by stsouko on 23.09.16.
 */
var customer={"structures": [{"data": "CCC"}]};

$.ajax({
        type: "POST",
        data :JSON.stringify(customer),
        url: "create?type=0",
        contentType: "application/json"
    });


$.ajax({
        type: "GET",
        url: "prepare?task=6dbcadfd-fd9b-4d3e-bd81-10dc6fa22d30",
        contentType: "application/json"
    });