
(function() {
	angular.module('launcher', ['indx'])
		.config(['$routeProvider', function($routeProvider) {
			$routeProvider
			.when('/', {templateUrl: 'templates/root.html', controller:"Root"})
			.when('/login', {templateUrl: 'templates/userlist.html',   controller:"Login"})
			.when('/logout', {templateUrl: 'templates/root.html',   controller:"Logout"})
			.when('/apps', {templateUrl: 'templates/appslist.html', controller:"AppsList"})
			.when('/boxeslist', {templateUrl:'templates/boxeslist.html', controller:'BoxesList'})
			.otherwise({redirectTo: '/'});
		}])
	.controller('Root', function($scope, $location, client, utils) {
		// root just redirects to appropriate places
		client.store.check_login().then(function(login) {
			if (login.is_authenticated) {
				u.safe_apply($scope, function() { $location.path('/apps'); });
			} else {
				console.log('routing to login');
				u.safe_apply($scope, function() { $location.path('/login'); });
			}
		});
	}).controller('Logout', function($scope, $location, client, utils) {
		// root just redirects to appropriate places
		console.log('route::logout', client);
		try{
			client.store.logout().then(function(login) {
				try {
					utils.safe_apply($scope, function() { $location.path('/login'); });
				} catch(e) { console.error(e); }
			}).fail(function(err) { console.error(err); });
		} catch(e) { console.error(e); }
	}).directive('user',function() {
		return {
			restrict:'E',
			templateUrl:'templates/user.html',
			scope:{user:"=model"},
			replace:true
		};
	}).controller('Login',function($scope, $location, client, backbone, utils) {
		console.log('route::login');
		var u = utils, store = client.store, sa = function(f) { return utils.safe_apply($scope,f);};
		$scope.user = {username:undefined, password:undefined};
		$scope.select_user = function(user) { $scope.user.username = user; };
		$scope.back_to_login = function() {	delete $scope.user.username; delete $scope.user.password;};
		// this gets called when the form is submitted
		$scope.do_submit = function() {
			console.log('logging in ', $scope.user.username, $scope.user.password);
			store.login($scope.user.username, $scope.user.password).then(function() {
				u.debug('login okay!');
				// sa($scope.back_to_login);
				sa(function() { $location.path('/apps'); });
			}).fail(function() {
				sa(function() {
					delete $scope.user.password;
					u.shake($($scope.el).find('input:password').parents('.password-dialog'));
				});
			});
		};
		store.get_user_list()
			.then(function(result) {  sa(function() { $scope.users = result; }); })
			.fail(function(err) { u.error(err); });
	}).controller('AppsList', function($scope, $location, client, utils) {
		console.log('hello apps list');
		var u = utils, store = client.store, sa = function(f) { return utils.safe_apply($scope,f); };
		var get_apps_list = function() {
			client.store.get_apps_list().then(function(apps) {
				console.log('got apps list', apps);
				sa(function() { $scope.apps = apps; });
			}).fail(function() {
				sa(function() { delete $scope.apps; });
				u.error('oops can\'t get apps - not ready i guess');
			});
		};
		get_apps_list();
	}).controller('main', function($location, $scope, client, utils) {
		var u = utils;
		// we want to route
		client.store.on('login', function() {
			// just route
			u.safe_apply($scope,function() { $location.path('/apps'); });
		});
		client.store.on('logout', function() {
			// route back to login
			u.safe_apply($scope,function() { $location.path('/login'); });
		});

		client.store.check_login().then(function(login) {
			if (login.is_authenticated) {
				u.safe_apply($scope, function() { $location.path('/apps'); });
			} else {
				console.log('routing to login');
				u.safe_apply($scope, function() { $location.path('/login'); });
			}
		});
	}).controller('BoxesList', function($location, $scope, client, utils) {
		var u = utils,store = client.store, sa = function(f) { return utils.safe_apply($scope,f); };
		var get_boxes_list = function() {
			store.get_box_list().then(function (boxes) {
				console.log('boxes --> ', boxes);
				sa(function() { $scope.boxes = boxes; });
			}).fail(function() {
				sa(function() { delete $scope.boxes; });
				u.error('oops can\'t get boxes - not ready i guess');
			});
		};
		store.on('login', get_boxes_list);
		get_boxes_list();
		$scope.create_new_box = false;
	}).directive('focusOnShow', function() {
		return {
			restrict:'A',
			controller:function($scope, $element, $attrs, $route, client, $location) {
				$scope.$watch($attrs['focusOnShow'], function() {
					if ($scope.$eval($attrs['focusOnShow'])) {
						// 100ms after transition
						setTimeout(function() { $element.focus(); }, 100);
					}
				});
				$scope.$on('$routeChangeSuccess', function(evt, one, two) {
					client.store.check_login().then(function(login) {
						if (!login.is_authenticated) {
							console.log('routing to login');
							u.safe_apply($scope, function() { $location.path('/login'); });
						}
					});
				});
			}
		};
	});
})();
// .directive('boxeslist',function() {
// 		return {
// 			restrict: 'E',
// 			replace: true,
// 			templateUrl: 'templates/boxeslist.html',
// 			link:function ($scope, $element) { $scope.el = $element;	},
// 			controller: function ($scope, client, utils) {
// 				var u = utils,
// 					store = client.store,
// 					sa = function(f) { return utils.safe_apply($scope,f); };
// 				var get_boxes_list = function() {
// 					store.get_box_list().then(function (boxes) {
// 						console.log('boxes --> ', boxes);
// 						sa(function() { $scope.boxes = boxes; });
// 					}).fail(function() {
// 						sa(function() { delete $scope.boxes; });
// 						u.error('oops can\'t get boxes - not ready i guess');
// 					});
// 				};

// 				store.on('login', get_boxes_list);
// 				get_boxes_list();
// 				$scope.create_new_box = false;
// 			}
// 		};
// 	})