(global["webpackJsonp"]=global["webpackJsonp"]||[]).push([["plugins/book/components/app-write-off-code"],{"110f":function(t,e,n){"use strict";n.r(e);var i=n("b2b4"),a=n.n(i);for(var u in i)["default"].indexOf(u)<0&&function(t){n.d(e,t,(function(){return i[t]}))}(u);e["default"]=a.a},"3b201":function(t,e,n){"use strict";var i=n("6aee"),a=n.n(i);a.a},"6aee":function(t,e,n){},"945d":function(t,e,n){"use strict";var i;n.d(e,"b",(function(){return a})),n.d(e,"c",(function(){return u})),n.d(e,"a",(function(){return i}));var a=function(){var t=this,e=t.$createElement;t._self._c},u=[]},b2b4:function(t,e,n){"use strict";Object.defineProperty(e,"__esModule",{value:!0}),e.default=void 0;var i={name:"app-write-off-code",props:{hidden:{type:Boolean,default:function(){return!1}},itemId:{type:String,default:function(){return"-1"}}},data:function(){return{file_path:""}},watch:{hidden:{handler:function(t){var e=this;!0===t&&this.$request({url:this.$api.book.clerk_code,data:{id:this.itemId}}).then((function(t){0===t.code&&(e.file_path=t.data.file_path)}))}}},methods:{hiddenHandler:function(){this.$emit("hiden",!1),this.file_path=""}}};e.default=i},e604:function(t,e,n){"use strict";n.r(e);var i=n("945d"),a=n("110f");for(var u in a)["default"].indexOf(u)<0&&function(t){n.d(e,t,(function(){return a[t]}))}(u);n("3b201");var r,f=n("f0c5"),o=Object(f["a"])(a["default"],i["b"],i["c"],!1,null,"2fe1eae7",null,!1,i["a"],r);e["default"]=o.exports}}]);
;(global["webpackJsonp"] = global["webpackJsonp"] || []).push([
    'plugins/book/components/app-write-off-code-create-component',
    {
        'plugins/book/components/app-write-off-code-create-component':(function(module, exports, __webpack_require__){
            __webpack_require__('543d')['createComponent'](__webpack_require__("e604"))
        })
    },
    [['plugins/book/components/app-write-off-code-create-component']]
]);
