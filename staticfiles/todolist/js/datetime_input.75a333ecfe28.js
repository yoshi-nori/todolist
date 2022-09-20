$(function() {
    // TodoModel limit_timeの入力
    $("#id_limit_time_0").dateDropper({
        large : true, 
        largeDefault : true, 
    });
    $("#id_limit_time_1").timeDropper({
        meridians : true, 
        format : "H:mm:00", 
        mousewheel : true, 
        init_animation : "fadeIn", 
        setCurrentTime : false, 
        borderColor : "#fd4741", 
        primaryColor : "#fd4741"
    });
});
